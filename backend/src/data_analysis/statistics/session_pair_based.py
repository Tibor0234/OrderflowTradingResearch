from decimal import Decimal

from data_analysis.statistics.base import BaseStatisticsAnalyzer
from data_analysis.utils import AnalysisType


class SessionPairBasedStatisticsAnalyzer(BaseStatisticsAnalyzer):
    """Tracks statistics independently for each matching session pair."""

    def __init__(self, symbol: str | None = None):
        super().__init__(AnalysisType.SESSION_PAIR_BASED, symbol)

    def start_session_pair(self, starting_balance: Decimal):
        if not self._is_enabled_for_current_session():
            return

        self.model.starting_balance = starting_balance
        self.model.equity = starting_balance
        self._max_equity = starting_balance
        self._reset()
        self.visualizer.on_session_start()
        self.visualizer.on_statistics_update()
