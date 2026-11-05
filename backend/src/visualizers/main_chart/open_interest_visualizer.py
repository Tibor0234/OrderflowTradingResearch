from analyzers.open_interest.model import OpenInterest
from analyzers.utils import OscillatorRecord
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class OpenInterestVisualizer:
    """Forwards open-interest initialization and candle updates."""

    def __init__(self, model: OpenInterest, chart_id: int | None):
        self.model = model
        self.chart_id = chart_id

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "resource_init",
            self._init_payload(),
        )

    def on_candle_close(self, record: OscillatorRecord):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "market_update",
            {
                "resource_type": "open_interest",
                "target": f"main_chart/{self.chart_id}",
                "time": record.time,
                "value": record.value,
            },
        )
        self.cache_current_snapshot()

    def cache_current_snapshot(self) -> None:
        cache_snapshot("resource_init", self._init_payload())

    def _init_payload(self) -> dict[str, object]:
        return {
            "resource_type": "open_interest",
            "target": f"main_chart/{self.chart_id}",
            "length": self.model.length,
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        return {
            "records": [
                {"time": record.time, "value": record.value}
                for record in self.model.content
            ],
        }
