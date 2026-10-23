from analyzers.order_book_imbalance.base_analyzer import BaseOrderBookImbalanceAnalyzer

class OrderBookImbalanceAnalyzer(BaseOrderBookImbalanceAnalyzer):
    """A simple order book imbalance analyzer with equal weighting for all levels."""
    
    def get_weight(self, i):
        """Return the weighting factor for the given order book level."""
        return 1