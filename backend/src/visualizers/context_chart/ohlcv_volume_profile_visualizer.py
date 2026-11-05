from analyzers.ohlcv_volume_profile.model import OHLCVVolumeProfile
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class OHLCVVolumeProfileVisualizer:
    """Forwards OHLCV volume-profile snapshots for a context chart."""

    def __init__(self, model: OHLCVVolumeProfile, chart_id: int | None):
        self.model = model
        self.chart_id = chart_id

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "resource_init",
            self._init_payload(),
        )

    def on_message(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "market_update",
            {
                "resource_type": "ohlcv_volume_profile",
                "target": f"context_chart/{self.chart_id}",
                **self._snapshot(),
            },
        )
        self.cache_current_snapshot()

    def cache_current_snapshot(self) -> None:
        cache_snapshot("resource_init", self._init_payload())

    def _init_payload(self) -> dict[str, object]:
        if self.model.period is None:
            raise RuntimeError("OHLCV volume profile period has not been assigned")
        return {
            "resource_type": "ohlcv_volume_profile",
            "target": f"context_chart/{self.chart_id}",
            "price_bin_count": self.model.price_bin_count,
            "value_area_pct": self.model.value_area_pct,
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        poc = self.model.poc
        value_area = self.model.value_area
        return {
            "time": self.model.start_time,
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
