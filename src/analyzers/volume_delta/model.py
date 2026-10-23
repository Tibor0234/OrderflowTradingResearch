from collections import deque
from analyzers.utils import OscillatorRecord

class VolumeDelta:
    """Stores current and historical volume delta records."""

    def __init__(self, length: int):
        """Initialize the volume delta history with the specified window length."""
        self.length = length

        self.history: deque[OscillatorRecord] = deque(maxlen=length)
        self.current: OscillatorRecord | None = None

    @property
    def content(self):
        """Return historical records together with the current record."""
        if self.current is None:
            return list(self.history)
        return list(self.history) + [self.current]