from collections import deque
from analyzers.utils import OscillatorRecord

class OpenInterest:
    """Stores open interest data and its historical aggregation."""

    def __init__(self, length: int = 200):
        """Initialize the open interest model with a specified history length."""
        self.length = length
        self.history: deque[OscillatorRecord] = deque(maxlen=length)
        self.current: OscillatorRecord | None = None

    @property
    def content(self):
        """Return the combined list of historical and current open interest records."""
        if self.current is None:
            return list(self.history)
        return list(self.history) + [self.current]