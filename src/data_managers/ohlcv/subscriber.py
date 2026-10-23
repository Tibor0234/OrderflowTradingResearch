from abc import ABC, abstractmethod
from data_managers.ohlcv.utils import OHLCVPeriod

class OHLCVManagerSubscriber(ABC):
    """Defines the interface for consumers of OHLCV manager updates."""

    def __init__(self):
        """Initialize the subscriber with its configured timeframe period."""
        self.period: OHLCVPeriod

    @abstractmethod
    def process_message(self, msg):
        """Handle an OHLCV update."""
        pass