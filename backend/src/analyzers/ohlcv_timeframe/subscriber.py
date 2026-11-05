from abc import ABC, abstractmethod

from data_managers.ohlcv.utils import OHLCVPeriod


class OHLCVTimeframeSubscriber(ABC):
    """Receives chart configuration from its OHLCV timeframe."""

    @abstractmethod
    def set_chart_id(self, chart_id: int | None, period: OHLCVPeriod):
        """Store the chart ID and period of the timeframe being subscribed to."""
        raise NotImplementedError
