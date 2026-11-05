class Candle:
    """Represents a single candlestick in a price chart."""

    def __init__(self, time, open):
        """Initialize a new candlestick with the given opening time and price."""
        self.time = time
        self.open = open
        self.high = open
        self.low = open
        self.close = open

    def update_candle(self, price):
        """Update the candlestick with a new price."""
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price