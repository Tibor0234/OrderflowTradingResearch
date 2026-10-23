from data_analysis.equity_curve.base import BaseEquityCurve
from global_services.data.provider import DataProvider

class SessionPairBasedEquityCurve(BaseEquityCurve):
    """Tracks equity independently for each session pair."""

    def __init__(self, refresh_rate=100, max_points=2_000):
        """Initialize the session-pair equity curve and its update state."""
        super().__init__(max_points=max_points)
        self.starting_equity = None
        
        self.refresh_rate = refresh_rate
        self.update_count = 0

    def is_initialized(self):
        """Return whether enough points have been recorded for the curve."""
        return len(self.content) >= 2
    
    def start_session_pair(self):
        """Reset the curve for a new session pair."""
        self._clear_content()
        self.update_count = 0
        self.starting_equity = None

    def update(self, equity):
        """Update the curve when the configured refresh interval is reached."""
        self.update_count += 1

        if self.starting_equity is None:
            self.starting_equity = equity

        if not self.is_initialized() or self.update_count >= self.refresh_rate:
            time = DataProvider().get_time()

            self._add_point(time, equity)
            self.last_chart_time = time

            self.update_count = 0