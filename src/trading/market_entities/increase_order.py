import uuid
from decimal import Decimal
from trading.market_entities.utils import Side, OrderType
from global_services.data.provider import DataProvider

class IncreaseOrder():
    """Represents an order used to increase an existing trade."""

    def __init__(self, value: Decimal, entry_price: Decimal, type: OrderType, leverage: float = 1.0, kill_after_fill = None, metadata: dict[str, object] | None = None):
        """Initialize the increase order with its execution parameters."""
        self.source_id: uuid.UUID | None = None
        self.side: Side | None = None
        self.type = type
        self.value = Decimal(value)
        self.entry_price = Decimal(entry_price) if entry_price is not None else None
        self.leverage = Decimal(leverage)
        self.metadata = dict(metadata) if metadata else {}
        self.is_shadow = False

        self.fill_time = None
        self.kill_after_fill = kill_after_fill

    def set_from_source(self, source_id: uuid.UUID, side: Side, is_shadow: bool):
        """Set the source trade and order side."""
        self.source_id = source_id
        self.side = side
        self.is_shadow = is_shadow

    def is_filled(self) -> bool:
        """Return whether the order has been fully filled."""
        return self.value <= 0

    def is_triggered(self) -> bool:
        """Return whether the order conditions are currently met."""
        if self.type == OrderType.MARKET:
            return True
        current_price = DataProvider().get_price()
        return (current_price - self.entry_price) * (-self.side.value) >= 0
    
    def on_partial_fill(self):
        """Record the timestamp of the latest partial fill."""
        self.fill_time = DataProvider().get_time()

    def is_killed(self):
        """Return whether the order has exceeded its post-fill lifetime."""
        now = DataProvider().get_time()
        if not self.kill_after_fill or not self.fill_time:
            return False
        return (now - self.fill_time) >= self.kill_after_fill

class IncreaseLimitOrder(IncreaseOrder):
    """Represents a limit order used to increase an existing trade."""
    def __init__(self, value: Decimal, entry_price: Decimal, leverage: float = 1.0, kill_after_fill: int = None, metadata: dict[str, object] | None = None):
        """Initialize an increase limit order."""
        super().__init__(value=value, entry_price=entry_price, type=OrderType.LIMIT, leverage=leverage, kill_after_fill=kill_after_fill, metadata=metadata)

class IncreaseMarketOrder(IncreaseOrder):
    """Represents a market order used to increase an existing trade."""

    def __init__(self, value: Decimal, leverage: float = 1.0, metadata: dict[str, object] | None = None):
        """Initialize an increase market order."""
        super().__init__(value=value, entry_price=None, type=OrderType.MARKET, leverage=leverage, kill_after_fill=None, metadata=metadata)