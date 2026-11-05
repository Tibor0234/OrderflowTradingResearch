import uuid
from decimal import Decimal
from trading.market_entities.utils import Side, OrderType
from global_services.data.provider import DataProvider

class StopOrder:
    """Represents an order triggered by a specified price condition."""

    def __init__(self, price: Decimal, type: OrderType, close_rate: float = 1.0, metadata: dict[str, object] | None = None):
        """Initialize the stop order with its trigger and execution parameters."""
        self.id = uuid.uuid4()
        self.source_id: uuid.UUID | None = None
        self.side: Side | None = None
        self.type = type
        self.price = Decimal(price) if price is not None else None
        self.close_rate = Decimal(close_rate)
        self.metadata = dict(metadata) if metadata else {}
        self.is_shadow = False
        
        self.remaining_close_margin: Decimal | None = None
        self.last_trade_margin: Decimal | None = None

    def update_remaining_close_margin(
        self,
        trade_margin: Decimal,
        filled_margin: Decimal | None = None,
    ) -> Decimal:
        """Track the remaining close target as the linked trade changes size."""
        if self.remaining_close_margin is None or self.last_trade_margin is None:
            self.remaining_close_margin = trade_margin * self.close_rate
        elif filled_margin is None:
            trade_margin_change = trade_margin - self.last_trade_margin
            self.remaining_close_margin += trade_margin_change * self.close_rate
        else:
            self.remaining_close_margin -= filled_margin

        self.remaining_close_margin = max(
            Decimal(0),
            self.remaining_close_margin,
        )
        self.last_trade_margin = trade_margin
        return self.remaining_close_margin

    def set_from_source(self, source_id: uuid.UUID, side: Side, is_shadow: bool):
        """Set the source trade and derive the closing order side."""
        self.source_id = source_id
        self.side = side.opposite()
        self.is_shadow = is_shadow

    def is_filled(self) -> bool:
        """Return whether the order has been fully executed."""
        return (
            self.remaining_close_margin is not None
            and self.remaining_close_margin <= 0
        )

    def is_triggered(self, direction: int) -> bool:
        """Return whether the current market price has reached the trigger price."""
        if self.price is None:
            return True
        current_price = DataProvider().get_price()
        return (current_price - self.price) * direction >= 0
    
    
class TakeProfit(StopOrder):
    """Represents a take-profit order that closes a portion of a trade."""

    def __init__(self, price: Decimal, type: OrderType, close_rate: float, metadata: dict[str, object] | None = None):
        """Initialize a take-profit order with the specified closing percentage."""
        super().__init__(price=price, type=type, close_rate=close_rate, metadata=metadata)

    def is_triggered(self):
        """Return whether the take-profit price has been reached."""
        return super().is_triggered(-self.side.value)

class StopLoss(StopOrder):
    """Represents a stop-loss order that closes a trade to prevent further losses."""

    def __init__(self, price: Decimal, close_rate: float, metadata: dict[str, object] | None = None):
        """Initialize a stop-loss order."""
        super().__init__(price=price, type=OrderType.MARKET, close_rate=close_rate, metadata=metadata)

    def is_triggered(self):
        """Return whether the stop-loss price has been reached."""
        return super().is_triggered(self.side.value)

class LiquidationOrder(StopOrder):
    """Represents a liquidation order that closes a trade when it is forcibly liquidated."""

    def __init__(self, price: Decimal, metadata: dict[str, object] | None = None):
        """Initialize a liquidation order."""
        super().__init__(price=price, type=OrderType.MARKET, close_rate=1.0, metadata=metadata)

    def is_triggered(self):
            """Return whether the stop-loss price has been reached."""
            return super().is_triggered(self.side.value)

class ReduceOnlyMarket(StopOrder):
    """Represents a reduce-only order that closes a portion of a trade regardless of market price."""

    def __init__(self, close_rate: float, metadata: dict[str, object] | None = None):
        """Initialize a reduce-only order with the specified closing percentage."""
        super().__init__(price=None, type=OrderType.MARKET, close_rate=close_rate, metadata=metadata)

    def is_triggered(self) -> bool:
        """Return whether the reduce-only order is considered triggered (always True)."""
        return True