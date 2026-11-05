from analyzers.utils import OscillatorRecord
from analyzers.volume_delta.model import VolumeDelta
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class VolumeDeltaVisualizer:
    """Forwards volume-delta initialization and candle updates."""

    def __init__(
        self,
        model: VolumeDelta,
        chart_id: int | None,
        resource_type: str,
        big_trades_analyzer=None,
    ):
        self.model = model
        self.chart_id = chart_id
        self.resource_type = resource_type
        self.big_trades_analyzer = big_trades_analyzer

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
                "resource_type": self.resource_type,
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
            "resource_type": self.resource_type,
            "target": f"main_chart/{self.chart_id}",
            "length": self.model.length,
            "big_trades": self.big_trades_analyzer is not None,
            "big_trades_pct": (
                self.big_trades_analyzer.top_pct
                if self.big_trades_analyzer is not None
                else 0
            ),
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        records = list(self.model.history)
        if self.model.current is not None and (
            not records or records[-1] is not self.model.current
        ):
            records.append(self.model.current)
        return {
            "records": [
                {"time": record.time, "value": record.value}
                for record in records
            ],
        }
