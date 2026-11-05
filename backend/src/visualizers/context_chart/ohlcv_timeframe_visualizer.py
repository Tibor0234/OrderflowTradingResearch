from analyzers.ohlcv_timeframe.model import OHLCVTimeframe
from data_managers.ohlcv.utils import OHLCVMessage
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class OHLCVTimeframeVisualizer:
    """Forwards OHLCV timeframe snapshots for a context chart."""

    def __init__(
        self,
        model: OHLCVTimeframe,
        chart_id: int | None,
    ):
        self.model = model
        self.chart_id = chart_id

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "resource_init",
            self._init_payload(),
        )

    def on_message(self, message: OHLCVMessage):
        snapshot = self._snapshot()
        snapshot["interval"] = message.interval
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "market_update",
            {
                "resource_type": "ohlcv_timeframe",
                "target": f"context_chart/{self.chart_id}",
                **snapshot,
            },
        )
        self._cache_snapshot(snapshot)

    def cache_current_snapshot(self) -> None:
        self._cache_snapshot(self._snapshot())

    def _cache_snapshot(self, snapshot: dict[str, object]) -> None:
        cache_snapshot("resource_init", self._init_payload(snapshot))

    def _init_payload(
        self,
        snapshot: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {
            "resource_type": "ohlcv_timeframe",
            "target": f"context_chart/{self.chart_id}",
            "period": self.model.period.value,
            "snapshot": self._snapshot() if snapshot is None else snapshot,
        }

    def _snapshot(self) -> dict[str, object]:
        return {
            "interval": self.model.interval,
            "candles": [
                {
                    "time": candle.time,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                }
                for candle in self.model.content
            ],
        }