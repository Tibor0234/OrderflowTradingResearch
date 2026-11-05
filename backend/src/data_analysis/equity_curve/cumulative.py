from decimal import Decimal

from data_analysis.equity_curve.base import BaseEquityCurveAnalyzer
from data_analysis.utils import AnalysisType
from global_services.data.provider import DataProvider
from visualizers.data_analysis.equity_curve_visualizer import EquityCurveVisualizer


class CumulativeEquityCurveAnalyzer(BaseEquityCurveAnalyzer):
    """Tracks cumulative equity across session pairs."""

    def __init__(self, symbol: str | None = None):
        super().__init__(AnalysisType.CUMULATIVE, symbol)
        self.enabled = self.model.symbol is None
        self.session_pair_boundaries = []
        self.last_chart_time = 0
        self.last_source_time = None
        self.visualizer = EquityCurveVisualizer(self.model)

    def is_initialized(self):
        return self.enabled and super().is_initialized()

    def start_session_pair(self, starting_balance: Decimal | None = None):
        """Reset sampling state while retaining points from previous pairs."""
        current_symbol = DataProvider().get_symbol()
        self.enabled = (
            self.model.symbol is None or current_symbol == self.model.symbol
        )
        if not self.enabled:
            return

        self._reset_sampling_state()
        self.last_source_time = None

    def update(self, equity):
        if self.enabled:
            super().update(equity)

    def record_trade_event(self, equity):
        if self.enabled:
            super().record_trade_event(equity)

    def record_session_pair_end(self, equity):
        if self.enabled:
            super().record_session_pair_end(equity)

    def _store_point(self, time, equity) -> int:
        if self.last_source_time is None:
            chart_time = self.last_chart_time + 1
            self.session_pair_boundaries.append(chart_time)
        else:
            chart_time = self.last_chart_time + max(time - self.last_source_time, 1)

        self.model.content[chart_time] = equity
        self.last_chart_time = chart_time
        self.last_source_time = time
        return chart_time