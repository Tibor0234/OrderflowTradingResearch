from decimal import Decimal
from data_managers.ohlcv.utils import OHLCVMessage, OHLCVPeriod
from analyzers.ohlcv_volume_profile.utils import OHLCVPriceBin, POC, ValueArea
from data_managers.ohlcv.utils import OHLCVMessage
from session_pairs.resource import Resource
from analyzers.ohlcv_timeframe.analyzer import OHLCVTimeframeSubscriber
from analyzers.ohlcv_volume_profile.model import OHLCVVolumeProfile

class OHLCVVolumeProfileAnalyzer(Resource, OHLCVTimeframeSubscriber):
    """Builds a volume profile from OHLCV candles and calculates its value area."""

    def __init__(self, price_bin_count=24, value_area_pct=70, visualize=True):
        """Initialize the volume profile analyzer with the specified configuration."""
        self.model: OHLCVVolumeProfile = OHLCVVolumeProfile(price_bin_count, value_area_pct)
        self.visualize = visualize

        self.poc_index = None

    @property
    def visualizer(self):
        """Return the volume profile visualizer when visualization is enabled."""
        if self.visualize:
            from visualizers.context_chart.volume_profile import OHLCVVolumeProfileVisualizer
            return OHLCVVolumeProfileVisualizer(self.model)
        return None

    def set_period(self, period: OHLCVPeriod):
        """Set the OHLCV timeframe period for the volume profile model."""
        self.model.period = period

    def reset(self):
        """Clear the volume profile and reset all calculated values."""
        self.model.content.clear()
        self.model.poc = None
        self.model.value_area = None
        self.poc_index = None
        self.model.start_time = None

    def on_ohlcv_timeframe_update(self, msg: OHLCVMessage):
        """Recalculate the volume profile from the latest timeframe candles."""
        self.model.start_time = min(c.time for c in msg.candles)

        volumes = [c.volume for c in msg.candles]
        lows = [c.low for c in msg.candles]
        highs = [c.high for c in msg.candles]

        min_price = min(lows)
        max_price = max(highs)

        price_range = max_price - min_price
        bin_size = price_range / Decimal(self.model.price_bin_count)

        bins = [
            OHLCVPriceBin(
                low=min_price + bin_size * i,
                size=bin_size,
                volume=Decimal(0),
            )
            for i in range(self.model.price_bin_count)
        ]

        poc_volume, poc_index = self._apply_volumes(
            msg.candles, volumes, bins, min_price, bin_size
        )

        self.model.content = bins
        self.model.poc = POC(
            price=bins[poc_index].low + bins[poc_index].size / 2,
            volume=poc_volume,
        )

        self.poc_index = poc_index
        
        self._calculate_value_area()

    def _apply_volumes(self, candles, volumes, bins, min_price, bin_size):
        """Distribute candle volume across price bins based on price overlap."""
        poc_volume = Decimal(0)
        poc_index = 0

        for candle, vol in zip(candles, volumes):
            if candle.high == candle.low:
                continue

            start_index = int((candle.low - min_price) / bin_size)
            end_index = int((candle.high - min_price) / bin_size)

            start_index = max(0, min(start_index, len(bins) - 1))
            end_index = max(0, min(end_index, len(bins) - 1))

            vol_range = candle.high - candle.low

            for i in range(start_index, end_index + 1):
                bin_low = bins[i].low
                bin_high = bin_low + bin_size

                overlap_low = max(bin_low, candle.low)
                overlap_high = min(bin_high, candle.high)
                overlap = max(Decimal(0), overlap_high - overlap_low)

                if overlap == 0:
                    continue

                weight = overlap / vol_range
                added_volume = vol * weight
                bins[i].volume += added_volume

                if bins[i].volume > poc_volume:
                    poc_volume = bins[i].volume
                    poc_index = i

        return poc_volume, poc_index

    def _calculate_value_area(self):
        """Calculate the value area of the volume profile based on the target volume."""
        bins = self.model.content

        total_volume = sum(b.volume for b in bins)
        target_volume = total_volume * self.model.value_area_rate

        poc_index = self.poc_index

        cum_volume = bins[poc_index].volume
        va_low = poc_index
        va_high = poc_index

        left = poc_index - 1
        right = poc_index + 1

        while cum_volume < target_volume:
            left_vol = bins[left].volume if left >= 0 else Decimal(-1)
            right_vol = bins[right].volume if right < len(bins) else Decimal(-1)

            if left_vol >= right_vol and left >= 0:
                cum_volume += left_vol
                va_low = left
                left -= 1
            elif right < len(bins):
                cum_volume += right_vol
                va_high = right
                right += 1
            else:
                break

        self.model.value_area = ValueArea(
            low=bins[va_low].low,
            high=bins[va_high].low + bins[va_high].size,
        )