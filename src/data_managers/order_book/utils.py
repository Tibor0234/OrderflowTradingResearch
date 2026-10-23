from decimal import Decimal
from dataclasses import dataclass

@dataclass(slots=True)
class OrderBookRow:
    """Represents a single order book level."""

    price: Decimal
    quantity: Decimal

@dataclass(slots=True)
class OrderBookMessage:
    """Contains a timestamped snapshot of bid and ask levels."""
    
    time: int
    bids: list[OrderBookRow]
    asks: list[OrderBookRow]