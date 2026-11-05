from abc import ABC, abstractmethod
from decimal import Decimal

from data_analysis.equity_curve.model import EquityCurve
from data_analysis.utils import AnalysisType
from global_services.data.provider import DataProvider
from visualizers.data_analysis.equity_curve_visualizer import EquityCurveVisualizer


class BaseEquityCurveAnalyzer(ABC):
    """Analyzes equity updates and records trade-event points and segment extrema."""

    def __init__(self, analysis_type: AnalysisType, symbol: str | None = None):
        self.model = EquityCurve(type=analysis_type, symbol=symbol)
        self.visualizer: EquityCurveVisualizer
        self._points_this_pair = 0
        self._has_point_in_pair = False
        self._segment_start: tuple[int, Decimal, int] | None = None
        self._segment_high: tuple[int, Decimal, int] | None = None
        self._segment_low: tuple[int, Decimal, int] | None = None
        self._observation_sequence = 0
        self._last_recorded_source_point: tuple[int, Decimal] | None = None

    def is_initialized(self):
        """Return whether at least two points have been recorded this session pair."""
        return self._points_this_pair >= 2

    def update(self, equity):
        """Track an observed equity value without storing every price update."""
        time = DataProvider().get_time()
        if self.model.starting_balance is None:
            self.model.starting_balance = equity

        if not self._has_point_in_pair:
            self._append_source_point(time, equity)
            self._has_point_in_pair = True
            self._start_segment(time, equity)
            return

        self._observe(time, equity)

    def record_trade_event(self, equity):
        """Store a trade boundary and finalize extrema from the preceding segment."""
        time = DataProvider().get_time()
        if self.model.starting_balance is None:
            self.model.starting_balance = equity

        if self._has_point_in_pair:
            self._flush_segment()

        self._append_source_point(time, equity)
        self._has_point_in_pair = True
        self._start_segment(time, equity)

    def record_session_pair_end(self, equity):
        """Finalize pending extrema and store the session-pair endpoint."""
        time = DataProvider().get_time()
        if self.model.starting_balance is None:
            self.model.starting_balance = equity

        if self._has_point_in_pair:
            self._flush_segment()

        if self._last_recorded_source_point != (time, equity):
            self._append_source_point(time, equity)

        self._has_point_in_pair = True
        self._start_segment(time, equity)

    def _reset_sampling_state(self):
        self._points_this_pair = 0
        self._has_point_in_pair = False
        self._segment_start = None
        self._segment_high = None
        self._segment_low = None
        self._observation_sequence = 0
        self._last_recorded_source_point = None

    def _start_segment(self, time, equity):
        point = self._new_observation(time, equity)
        self._segment_start = point
        self._segment_high = point
        self._segment_low = point

    def _observe(self, time, equity):
        point = self._new_observation(time, equity)
        if self._segment_high is None or equity > self._segment_high[1]:
            self._segment_high = point
        if self._segment_low is None or equity < self._segment_low[1]:
            self._segment_low = point

    def _new_observation(self, time, equity):
        self._observation_sequence += 1
        return time, equity, self._observation_sequence

    def _flush_segment(self):
        points = []
        for point in (self._segment_high, self._segment_low):
            if (
                point is not None
                and point != self._segment_start
                and point not in points
            ):
                points.append(point)

        for time, equity, _ in sorted(points, key=lambda point: (point[0], point[2])):
            self._append_source_point(time, equity)

    def _append_source_point(self, time, equity):
        chart_time = self._store_point(time, equity)
        self._points_this_pair += 1
        self._last_recorded_source_point = (time, equity)
        self.visualizer.on_equity_curve_update(chart_time, equity)

    @abstractmethod
    def _store_point(self, time, equity) -> int:
        """Store an observed point using the curve's time axis."""

    @abstractmethod
    def start_session_pair(self, starting_balance: Decimal | None = None):
        """Reset the sampling state for a new session pair."""

    def init_frontend(self):
        self.visualizer.init_frontend()
