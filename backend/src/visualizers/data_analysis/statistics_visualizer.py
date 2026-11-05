from data_analysis.statistics.model import Statistics
from data_analysis.utils import AnalysisType
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class StatisticsVisualizer:
    """Forwards statistics initialization, updates, and session resets."""

    def __init__(self, model: Statistics):
        self.model = model

    @property
    def target(self):
        return f"statistics/{self.model.type.value}_{self.model.symbol}"

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "analysis_init",
            self._init_payload(),
        )

    def on_statistics_update(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "analysis_update",
            {
                "analysis_type": "statistics",
                "target": self.target,
                "statistics": self._snapshot(),
            },
        )
        self.cache_current_snapshot()

    def on_session_start(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "analysis_session_start",
            {
                "analysis_type": "statistics",
                "target": self.target,
            },
        )
        self.cache_current_snapshot()

    def cache_current_snapshot(self) -> None:
        cache_snapshot("analysis_init", self._init_payload())

    def _init_payload(self) -> dict[str, object]:
        if self.model.symbol:
            name = self.model.symbol
        elif self.model.type is AnalysisType.SESSION_PAIR_BASED:
            name = "Session Pair"
        else:
            name = "Full Run"
        return {
            "analysis_type": "statistics",
            "target": self.target,
            "name": name,
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        model = self.model
        return {
            "total_trades": model.total_trades,
            "winrate": f"{model.winrate}" if model.winrate is not None else None,
            "pnl": f"{model.pnl}",
            "roi": f"{model.roi}",
            "max_drawdown": f"{model.max_drawdown}",
            "average_trade_duration": model.average_trade_duration,
        }
