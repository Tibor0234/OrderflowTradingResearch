from abc import ABC, abstractmethod

class TimeframeSubscriber(ABC):
    """Interface for consumers that need timeframe initialization and close events."""

    def bind_to_timeframe(self, length: int, chart_id: int | None = None):
        """Bind the subscriber to a timeframe and its chart context."""
        pass

    @abstractmethod
    def on_candle_close(self, next_time: int | None = None):
        """Handle the event when the timeframe closes a candle."""
        pass