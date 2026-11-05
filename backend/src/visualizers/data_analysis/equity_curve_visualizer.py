from data_analysis.equity_curve.model import EquityCurve
from data_analysis.utils import AnalysisType
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class EquityCurveVisualizer:
    """Forwards equity-curve initialization, point updates, and session resets."""

    def __init__(self, model: EquityCurve):
        self.model = model

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "analysis_init",
            self._init_payload(),
        )

    def on_equity_curve_update(self, time, equity):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "analysis_update",
            {
                "analysis_type": "equity_curve",
                "target": f"equity_curve/{self.model.type.value}_{self.model.symbol}",
                "time": time,
                "equity": str(equity),
                "starting_balance": self._starting_balance_value(),
            },
        )
        self.cache_current_snapshot()

    def on_session_start(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "analysis_session_start",
            {
                "analysis_type": "equity_curve",
                "target": f"equity_curve/{self.model.type.value}_{self.model.symbol}",
            },
        )
        self.cache_current_snapshot()

    def cache_current_snapshot(self) -> None:
        cache_snapshot("analysis_init", self._init_payload())

    def _init_payload(self) -> dict[str, object]:
        if self.model.symbol:
            name = self.model.symbol
        elif self.model.type == AnalysisType.SESSION_PAIR_BASED:
            name = "Session Pair"
        else:
            name = "Full Run"
        return {
            "analysis_type": "equity_curve",
            "target": f"equity_curve/{self.model.type.value}_{self.model.symbol}",
            "name": name,
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        return {
            "starting_balance": self._starting_balance_value(),
            "points": [
                {"time": time, "equity": str(equity)}
                for time, equity in sorted(self.model.content.items())
            ],
        }

    def _starting_balance_value(self) -> str | None:
        if self.model.starting_balance is None:
            return None
        return str(self.model.starting_balance)