from collections import deque
from analyzers.utils import OscillatorRecord

class MicropriceDeviation:
    """Stores a rolling series of microprice deviation values."""

    def __init__(self, length: int = 10):
        """Initialize the model with a rolling window of oscillator records."""
        self.length = length
        self.content: deque[OscillatorRecord] = deque(maxlen=length)

    @property
    def current(self):
        """Return the most recent oscillator record, if available."""
        return self.content[-1] if self.content else None