from collections import deque
from analyzers.utils import OscillatorRecord

class OrderBookImbalance:
    """Stores order book imbalance data and its historical aggregation."""

    def __init__(self, depth: int = 20, length: int = 10):
        """Initialize the order book imbalance model with the specified depth and history length."""
        self.depth = depth
        self.length = length
        self.content: deque[OscillatorRecord] = deque(maxlen=length)

    @property
    def current(self):
        """Return the most recent order book imbalance record, or None if no records exist."""
        return self.content[-1] if self.content else None