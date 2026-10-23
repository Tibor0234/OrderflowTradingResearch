from data_analysis.equity_curve.base import BaseEquityCurve
from global_services.data.provider import DataProvider

class CumulativeEquityCurve(BaseEquityCurve):
    """Tracks cumulative equity across session pairs."""

    def __init__(self, refresh_rate=1_000, max_points=2_000):
        """Initialize the cumulative equity curve and its update state."""
        super().__init__(max_points=max_points)
        self.starting_equity = None
        self.session_pair_boundaries = []
        
        self.refresh_rate = refresh_rate
        self.update_count = 0

        self.last_chart_time = 0
        self.last_source_time = None
        self.session_pair_point_count = 0
        self.session_pair_start = None

    def is_initialized(self):
        """Return whether enough points have been recorded for the curve."""
        return self.session_pair_point_count >= 2
    
    def start_session_pair(self):
        """Reset the state used to track a new session pair."""
        self.session_pair_point_count = 0
        self.update_count = 0
        self.session_pair_start = None
        self.last_source_time = None

    def update(self, equity):
        """Update the curve when the configured refresh interval is reached."""
        self.update_count += 1

        if self.starting_equity is None:
            self.starting_equity = equity

        if not self.is_initialized() or self.update_count >= self.refresh_rate:
            time = DataProvider().get_time()

            if self.last_source_time is None:
                chart_time = self.last_chart_time + 1
                self.session_pair_boundaries.append(chart_time)
            else:
                chart_time = self.last_chart_time + max(time - self.last_source_time, 1)

            self._add_point(chart_time, equity)
            self.last_chart_time = chart_time
            self.last_source_time = time

            self.session_pair_point_count += 1
            self.update_count = 0