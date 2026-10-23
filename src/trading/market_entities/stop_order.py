import uuid
from decimal import Decimal
from trading.market_entities.utils import Side, OrderType
from global_services.data.provider import DataProvider

class StopOrder:
    """Represents an order triggered by a specified price condition."""

    def __init__(self, price: Decimal, type: OrderType, close_rate: float = 1.0, metadata: dict[str, object] | None = None):
        """Initialize the stop order with its trigger and execution parameters."""
        self.source_id: uuid.UUID | None = None
        self.side: Side | None = None
        self.type = type
        self.price = Decimal(price) if price is not None else None
        self.close_rate = Decimal(close_rate)
        self.metadata = dict(metadata) if metadata else {}
        self.is_shadow = False

    def set_from_source(self, source_id: uuid.UUID, side: Side, is_shadow: bool):
        """Set the source trade and derive the closing order side."""
        self.source_id = source_id
        self.side = side.opposite()
        self.is_shadow = is_shadow

    def is_filled(self) -> bool:
        """Return whether the order has been fully executed."""
        return self.close_rate <= 0

    def is_triggered(self, direction: int) -> bool:
        """Return whether the current market price has reached the trigger price."""
        if self.price is None:
            return True
        current_price = DataProvider().get_price()
        return (current_price - self.price) * direction >= 0
    
    
class TakeProfit(StopOrder):
    """Represents a take-profit order that closes a portion of a trade."""

    def __init__(self, price: Decimal, type: OrderType, pct: float, metadata: dict[str, object] | None = None):
        """Initialize a take-profit order with the specified closing percentage."""
        super().__init__(price=price, type=type, close_rate=pct/100, metadata=metadata)

    def is_triggered(self):
        """Return whether the take-profit price has been reached."""
        return super().is_triggered(-self.side.value)

class StopLoss(StopOrder):
    """Represents a stop-loss order that closes a trade to prevent further losses."""

    def __init__(self, price: Decimal, metadata: dict[str, object] | None = None):
        """Initialize a stop-loss order."""
        super().__init__(price=price, type=OrderType.MARKET, close_rate=1.0, metadata=metadata)

    def is_triggered(self):
        """Return whether the stop-loss price has been reached."""
        return super().is_triggered(self.side.value)

class LiquidationOrder(StopLoss):
    """Represents a liquidation order that closes a trade when it is forcibly liquidated."""

    def __init__(self, price):
        """Initialize a liquidation order."""
        super().__init__(price)

class ReduceOnly(StopOrder):
    """Represents a reduce-only order that closes a portion of a trade regardless of market price."""

    def __init__(self, pct: float, metadata: dict[str, object] | None = None):
        """Initialize a reduce-only order with the specified closing percentage."""
        super().__init__(price=None, type=OrderType.MARKET, close_rate=pct/100, metadata=metadata)

    def is_triggered(self) -> bool:
        """Return whether the reduce-only order is considered triggered (always True)."""
        return True