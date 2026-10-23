from data_managers.ohlcv.utils import OHLCVPeriod, OHLCVCandle

class OHLCVTimeframe:
    """Stores OHLCV candles for a specific timeframe period."""

    def __init__(self, period: OHLCVPeriod):
        """Initialize the model for the specified timeframe period."""
        self.period = period
        self.timeframe = None
        self.content: list[OHLCVCandle] = []

    @property
    def current(self):
        """Return the most recent candle, if available."""
        return self.content[-1] if self.content else None