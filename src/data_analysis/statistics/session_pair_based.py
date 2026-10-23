from data_analysis.statistics.base import BaseStatistics

class SessionPairBasedStatistics(BaseStatistics):
    """Tracks trading statistics independently for each session pair."""

    def __init__(self):
        """Initialize the session-pair statistics tracker."""
        super().__init__()

    def session_pair_start(self, starting_balance):
        """Reset and initialize statistics for a new session pair."""
        self.starting_balance = starting_balance
        self.equity = starting_balance
        self._max_equity = starting_balance
        self._update_count = 0
        self._reset()
