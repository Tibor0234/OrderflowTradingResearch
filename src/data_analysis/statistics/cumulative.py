from data_analysis.statistics.base import BaseStatistics

class CumulativeStatistics(BaseStatistics):
    """Tracks cumulative trading statistics across all session pairs."""
    
    def __init__(self):
        """Initialize the cumulative statistics tracker."""
        self.starting_balance = None
        super().__init__()
    
    def session_pair_start(self, starting_balance):
        """Initialize cumulative statistics when the first session pair starts."""
        if self.starting_balance is None:
            self.starting_balance = starting_balance
            self.equity = starting_balance
            self._max_equity = starting_balance
            self._update_count = 0