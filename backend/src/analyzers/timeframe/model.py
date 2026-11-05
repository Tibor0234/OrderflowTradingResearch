from collections import deque
from analyzers.timeframe.candle import Candle

class Timeframe:
    """Represents the timeframe model, maintaining a history of candles and the current candle."""
    def __init__(self, length: int):
        """Initialize the timeframe model with a specified history length."""
        self.length = length

        self.history: deque[Candle] = deque(maxlen=length - 1)
        self.current: Candle | None = None

    @property
    def content(self):
        """Return the complete list of candles, including the current one if it exists."""
        if self.current is None:
            return list(self.history)
        return list(self.history) + [self.current]