from decimal import Decimal

from data_analysis.statistics.base import BaseStatisticsAnalyzer
from data_analysis.utils import AnalysisType


class CumulativeStatisticsAnalyzer(BaseStatisticsAnalyzer):
    """Tracks cumulative statistics across matching session pairs."""

    def __init__(self, symbol: str | None = None):
        super().__init__(AnalysisType.CUMULATIVE, symbol)

    def start_session_pair(self, starting_balance: Decimal):
        if not self._is_enabled_for_current_session():
            return

        if self.model.starting_balance is None:
            self.model.starting_balance = starting_balance
            self.model.equity = starting_balance
            self._max_equity = starting_balance
            self.visualizer.on_statistics_update()