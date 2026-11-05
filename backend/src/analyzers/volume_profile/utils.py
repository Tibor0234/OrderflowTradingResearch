from dataclasses import dataclass
from decimal import Decimal

@dataclass(slots=True)
class PriceBin:
    """Represents a price range with separated buy and sell volume."""

    low: Decimal
    size: Decimal
    buy_volume: Decimal
    sell_volume: Decimal

    @property
    def volume(self) -> Decimal:
        return self.buy_volume + self.sell_volume

@dataclass(slots=True)
class Volume:
    """Stores aggregated buy and sell volume within a price range."""

    high: Decimal | None
    low: Decimal | None
    buy_volume: Decimal
    sell_volume: Decimal

    @property
    def volume(self) -> Decimal:
        return self.buy_volume + self.sell_volume

@dataclass(slots=True)
class POC:
    """Stores the point of control and its volume."""

    price: Decimal | None
    volume: Decimal

@dataclass(slots=True)
class ValueArea:
    """Stores the upper and lower boundaries of the value area."""
    
    high: Decimal | None
    low: Decimal | None