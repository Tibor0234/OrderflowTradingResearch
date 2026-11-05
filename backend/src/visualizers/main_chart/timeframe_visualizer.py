from analyzers.timeframe.candle import Candle
from analyzers.timeframe.model import Timeframe
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class TimeframeVisualizer:
    """Forwards timeframe initialization and candle updates."""

    def __init__(self, model: Timeframe, chart_id: int | None, candle_seconds: int):
        self.model = model
        self.chart_id = chart_id
        self.candle_seconds = candle_seconds

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "resource_init",
            self._init_payload(),
        )

    def on_candle_close(self, candle: Candle):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "market_update",
            {
                "resource_type": "timeframe",
                "target": f"main_chart/{self.chart_id}",
                "time": candle.time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
            },
        )
        self.cache_current_snapshot()

    def cache_current_snapshot(self) -> None:
        cache_snapshot("resource_init", self._init_payload())

    def _init_payload(self) -> dict[str, object]:
        return {
            "resource_type": "timeframe",
            "target": f"main_chart/{self.chart_id}",
            "candle_seconds": self.candle_seconds,
            "length": self.model.length,
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        return {
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
