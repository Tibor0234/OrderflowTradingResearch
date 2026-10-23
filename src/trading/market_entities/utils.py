from enum import Enum

class Side(Enum):
    """Defines the direction of a trade or order."""

    BUY = 1
    SELL = -1

    def opposite(self):
        """Return the opposite trading side."""
        return Side.BUY if self == Side.SELL else Side.SELL

class OrderType(Enum):
    """Defines the supported order execution types."""
    
    MARKET = 'market'
    LIMIT = 'limit'