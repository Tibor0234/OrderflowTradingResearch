from abc import ABC, abstractmethod
from data_managers.ohlcv.utils import OHLCVPeriod, OHLCVMessage

class OHLCVTimeframeSubscriber(ABC):
    """Defines the interface for consumers of OHLCV timeframe updates."""

    @abstractmethod
    def set_period(self, period: OHLCVPeriod):
        """Set the OHLCV timeframe period used by the subscriber."""
        pass

    @abstractmethod
    def on_ohlcv_timeframe_update(self, msg: OHLCVMessage):
        """Handle an update from the OHLCV timeframe analyzer."""
        pass