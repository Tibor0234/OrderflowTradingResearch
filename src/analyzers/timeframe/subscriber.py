from abc import ABC, abstractmethod
from data_managers.trade.utils import TradeMessage

class TimeframeSubscriber(ABC):
    """Abstract base class for subscribers to the timeframe analyzer."""

    def init_model(self, length):
        """Initialize the subscriber's model with the specified history length."""
        pass

    @abstractmethod
    def on_timeframe_update(self, msg: TradeMessage):
        """Handle an update from the timeframe analyzer with a new trade message."""
        pass

    @abstractmethod
    def on_candle_close(self, next_time: int | None = None):
        """Handle the event when a candle is closed, optionally providing the next candle's opening time."""
        pass