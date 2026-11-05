from analyzers.volume_profile.model import VolumeProfile
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class VolumeProfileVisualizer:
    """Forwards volume-profile initialization and candle snapshots."""

    def __init__(self, model: VolumeProfile, chart_id: int | None, length: int):
        self.model = model
        self.chart_id = chart_id
        self.length = length
        self._last_time: int | None = None

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "resource_init",
            self._init_payload(),
        )

    def on_candle_close(self, next_open: int | None):
        self._last_time = next_open
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "market_update",
            {
                "resource_type": "volume_profile",
                "target": f"main_chart/{self.chart_id}",
                **self._snapshot(),
            },
        )
        self.cache_current_snapshot()

    def cache_current_snapshot(self) -> None:
        cache_snapshot("resource_init", self._init_payload())

    def reset(self) -> None:
        self._last_time = None
        self.cache_current_snapshot()

    def _init_payload(self) -> dict[str, object]:
        return {
            "resource_type": "volume_profile",
            "target": f"main_chart/{self.chart_id}",
            "price_bin_count": self.model.price_bin_count,
            "value_area_pct": self.model.value_area_pct,
            "length": self.length,
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        poc = self.model.poc
        value_area = self.model.value_area
        return {
            "time": self._last_time,
            "bins": [
                {
                    "low": price_bin.low,
                    "size": price_bin.size,
                    "volume": price_bin.volume,
                }
                for price_bin in self.model.content
            ],
            "poc": (
                {"price": poc.price, "volume": poc.volume}
                if poc is not None
                else None
            ),
            "value_area": (
                {"low": value_area.low, "high": value_area.high}
                if value_area is not None
                else None
            ),
        }
