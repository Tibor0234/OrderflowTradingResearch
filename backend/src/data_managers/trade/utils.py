from trading.market_entities.utils import Side
from dataclasses import dataclass
from decimal import Decimal

@dataclass(slots=True)
class TradeMessage:
    """Represents a single trade message."""
    
    time: int
    price: Decimal
    quantity: Decimal
    side: Side