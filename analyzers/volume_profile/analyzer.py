from collections import deque
from decimal import Decimal

from session_pairs.price_chart_resource import PriceChartResource
from analyzers.timeframe.analyzer import TimeframeSubscriber
from data_managers.trade.utils import TradeMessage
from trading.market_entities.utils import Side

from analyzers.volume_profile.utils import PriceBin, POC, ValueArea, Volume
from analyzers.volume_profile.model import VolumeProfile


class VolumeProfileAnalyzer(PriceChartResource, TimeframeSubscriber):
    """Builds and maintains a rolling volume profile from trade data."""

    def __init__(self, price_bin_count=24, value_area_pct=70, length=100, visualize=True, chart_slot: int | None = None):
        """Initialize the volume profile analyzer with the specified configuration."""
        super().__init__(chart_slot)
        self.visualize = visualize

        self.model: VolumeProfile = VolumeProfile(
            price_bin_count=price_bin_count,
            value_area_pct=value_area_pct,
            length=length,
        )

        self.value_area_rate = Decimal(value_area_pct / 100)
        self.source: deque[Volume] = deque(maxlen=length)
        self.poc_index: int | None = None

    @property
    def visualizer(self):
        """Return the volume profile visualizer when visualization is enabled."""
        if self.visualize:
            from visualizers.price_chart.volume_profile import VolumeProfileVisualizer
            return VolumeProfileVisualizer(self.model, self.chart_slot)
        return None

    def reset(self):
        """Clear the volume profile and reset all calculated state."""
        m = self.model

        m.content.clear()
        self.source.clear()
        m.current = None

        m.poc = None
        m.value_area = None

        self.poc_index = None

    def on_timeframe_update(self, msg: TradeMessage):
        """Update the current volume profile with a new trade message."""
        m = self.model

        if m.current is None:
            m.current = Volume(
                high=msg.price,
                low=msg.price,
                buy_volume=Decimal(0),
                sell_volume=Decimal(0)
            )

        vol = m.current

        if vol.high is None or msg.price > vol.high:
            vol.high = msg.price

        if vol.low is None or msg.price < vol.low:
            vol.low = msg.price

        if msg.side == Side.BUY:
            vol.buy_volume += msg.quantity
        else:
            vol.sell_volume += msg.quantity

    def on_candle_close(self, next_open: int | None = None):
        """Update the rolling profile and recalculate its derived metrics."""
        m = self.model

        deprecated = None
        if len(self.source) == self.source.maxlen:
            deprecated = self.source.popleft()  # ✅ FIX: helyes eltávolítás

        self.source.append(m.current)

        if not m.content:
            self.build_profile()
        else:
            current_low = m.current.low
            current_high = m.current.high

            content_low = m.content[0].low
            content_high = m.content[-1].low + m.content[-1].size

            rebuild_needed = (
                current_low < content_low or
                current_high > content_high or
                (deprecated and (
                    deprecated.low == content_low or
                    deprecated.high == content_high
                ))
            )

            if rebuild_needed:
                self.build_profile()
            else:
                self.update_profile(m.current, deprecated)

        self.calculate_poc(m.content)

        self.calculate_value_area(m.content)

        m.current = None

    def _apply_volume(self, vol: Volume, bins: list[PriceBin], min_price, bin_size, sign):
        """Distribute volume across price bins based on price overlap."""
        if vol.low is None or vol.high is None or vol.high == vol.low:
            return

        start_index = int((vol.low - min_price) / bin_size)
        end_index = int((vol.high - min_price) / bin_size)

        start_index = max(0, min(start_index, len(bins) - 1))
        end_index = max(0, min(end_index, len(bins) - 1))

        for i in range(start_index, end_index + 1):
            bin_low = bins[i].low
            bin_high = bin_low + bin_size

            overlap_low = max(bin_low, vol.low)
            overlap_high = min(bin_high, vol.high)
            overlap = max(Decimal(0), overlap_high - overlap_low)

            vol_range = vol.high - vol.low

            if vol_range > 0 and overlap > 0:
                weight = overlap / vol_range

                bins[i].buy_volume += sign * vol.buy_volume * weight
                bins[i].sell_volume += sign * vol.sell_volume * weight

    def build_profile(self):
        """Rebuild the volume profile from the complete rolling source."""
        m = self.model

        lows = [v.low for v in self.source if v.low is not None]
        highs = [v.high for v in self.source if v.high is not None]

        if not lows or not highs:
            return

        min_price = min(lows)
        max_price = max(highs)

        if min_price == max_price:
            return

        bin_size = (max_price - min_price) / Decimal(m.price_bin_count)

        bins = [
            PriceBin(
                low=min_price + bin_size * i,
                size=bin_size,
                buy_volume=Decimal(0),
                sell_volume=Decimal(0)
            )
            for i in range(m.price_bin_count)
        ]

        for vol in self.source:
            self._apply_volume(vol, bins, min_price, bin_size, sign=1)

        # ✅ FIX: inplace update
        m.content.clear()
        m.content.extend(bins)

    def update_profile(self, current_volume, deprecated_volume=None):
        """Incrementally update the profile with new and expired volume."""
        m = self.model

        if not m.content:
            return

        min_price = m.content[0].low
        bin_size = m.content[0].size

        self._apply_volume(current_volume, m.content, min_price, bin_size, sign=1)

        if deprecated_volume:
            self._apply_volume(deprecated_volume, m.content, min_price, bin_size, sign=-1)

    def calculate_poc(self, bins: list[PriceBin]):
        """Calculate the point of control from the current price bins."""
        m = self.model

        if not bins:
            m.poc = None
            self.poc_index = None
            return

        max_volume = Decimal(0)
        poc_index = None

        for i, b in enumerate(bins):
            if b.volume > max_volume or poc_index is None:
                max_volume = b.volume
                poc_index = i

        if poc_index is None:
            m.poc = None
            self.poc_index = None
            return

        self.poc_index = poc_index

        m.poc = POC(
            price=bins[poc_index].low + bins[poc_index].size / 2,
            volume=max_volume
        )

    def calculate_value_area(self, bins: list[PriceBin]):
        """Calculate the value area around the point of control."""
        m = self.model

        if not bins or self.poc_index is None:
            m.value_area = None
            return

        total_volume = sum(b.volume for b in bins)

        if total_volume == 0:
            m.value_area = None
            return

        target = total_volume * self.value_area_rate

        poc_idx = self.poc_index

        left = poc_idx - 1
        right = poc_idx + 1

        va_low = poc_idx
        va_high = poc_idx

        cum = bins[poc_idx].volume

        while cum < target:
            left_vol = bins[left].volume if left >= 0 else Decimal(-1)
            right_vol = bins[right].volume if right < len(bins) else Decimal(-1)

            if left_vol >= right_vol and left >= 0:
                cum += left_vol
                va_low = left
                left -= 1
            elif right < len(bins):
                cum += right_vol
                va_high = right
                right += 1
            else:
                break

        m.value_area = ValueArea(
            low=bins[va_low].low,
            high=bins[va_high].low + bins[va_high].size
        )