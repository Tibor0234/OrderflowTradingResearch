from decimal import Decimal

from data_analysis.equity_curve.base import BaseEquityCurveAnalyzer
from data_analysis.utils import AnalysisType
from visualizers.data_analysis.equity_curve_visualizer import EquityCurveVisualizer


class SessionPairBasedEquityCurveAnalyzer(BaseEquityCurveAnalyzer):
    """Tracks equity independently for each session pair."""

    def __init__(self):
        super().__init__(AnalysisType.SESSION_PAIR_BASED)
        self.last_chart_time = None
        self.visualizer = EquityCurveVisualizer(self.model)

    def start_session_pair(self, starting_balance: Decimal | None = None):
        """Clear the curve and reset sampling for a new session pair."""
        self.model.content.clear()
        self.model.starting_balance = None
        self.last_chart_time = None
        self._reset_sampling_state()
        self.visualizer.on_session_start()

    def _store_point(self, time, equity) -> int:
        chart_time = time
        if self.last_chart_time is not None and chart_time <= self.last_chart_time:
            chart_time = self.last_chart_time + 1

        self.model.content[chart_time] = equity
        self.last_chart_time = chart_time
        return chart_time