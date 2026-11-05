from analyzers.order_book_imbalance.base_analyzer import BaseOrderBookImbalanceAnalyzer

class OrderBookWeightedImbalanceAnalyzer(BaseOrderBookImbalanceAnalyzer):
    """An order book imbalance analyzer that applies increasing weights to deeper levels."""

    def get_weight(self, i):
        """Return the weighting factor for the given order book level."""
        return i + 1