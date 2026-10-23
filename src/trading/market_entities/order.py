import uuid
from abc import ABC
from trading.market_entities.utils import Side, OrderType
from decimal import Decimal
from global_services.data.provider import DataProvider
from trading.market_entities.stop_order import StopOrder
from trading.market_entities.increase_order import IncreaseOrder, IncreaseLimitOrder

class Order(ABC):
    """Represents a base order with execution and lifetime management."""

    def __init__(
        self,
        side: Side,
        value: Decimal,
        entry_price: Decimal,
        type: OrderType,
        leverage: float,
        kill: int = None,
        kill_after_fill: int = None,
        metadata: dict[str, object] | None = None,
        is_shadow: bool = False,
    ):
        """Initialize the order with its execution parameters and lifetime settings."""
        self.id = uuid.uuid4()
        self.type: OrderType = type
        self.side: Side = side
        self.entry_price: Decimal = entry_price
        self.value: Decimal = value
        self.leverage: Decimal = Decimal(leverage)
        self.metadata = dict(metadata) if metadata else {}
        self.is_shadow = is_shadow

        # Kill timings
        self.kill: int | None = kill
        self.kill_after_fill: int | None = kill_after_fill
        self.place_time: int | None = None
        self.fill_time: int | None = None


    def place(self):
        """Record the order placement timestamp."""
        self.place_time = DataProvider().get_time()

    def on_partial_fill(self):
        """Record the timestamp of a partial fill."""
        self.fill_time = DataProvider().get_time()

    def is_filled(self) -> bool:
        """Return whether the order has been fully filled."""
        return self.value <= 0

    def is_killed(self) -> bool:
        """Return whether the order has exceeded its configured lifetime."""
        now = DataProvider().get_time()
        
        if not self.place_time:
            return False

        if not self.fill_time:
            if self.kill and (now - self.place_time) >= self.kill:
                return True
        else:
            if self.kill_after_fill and (now - self.fill_time) >= self.kill_after_fill:
                return True

        return False

    def link(self, linked_order: IncreaseOrder | StopOrder):
        """Link an increase or stop order to this order."""
        linked_order.set_from_source(self.id, self.side, self.is_shadow)
        return self
    
    def link_many(self, linked_orders: list[IncreaseOrder | StopOrder]):
        """Link multiple increase or stop orders to this order."""
        if not isinstance(linked_orders, list):
            linked_orders = [linked_orders]
        
        for linked_order in linked_orders:
            self.link(linked_order)
            
        return self

    def is_triggered(self) -> bool:
        """Return whether the order conditions are currently met."""
        if self.type == OrderType.MARKET:
            return True
        price = DataProvider().get_price()
        return (price - self.entry_price) * (-self.side.value) >= 0
    
    def convert_to_increase_order(self) -> IncreaseLimitOrder:
        """Convert the order into an increase limit order."""
        increase_order = IncreaseLimitOrder(
            self.value,
            self.entry_price,
            self.leverage,
            self.kill_after_fill,
            self.metadata,
        )
        increase_order.is_shadow = self.is_shadow
        return increase_order


class LimitOrder(Order):
    """Represents a limit order with a specified entry price."""

    def __init__(self, side: Side, value: Decimal, entry_price: Decimal, leverage: float = 1.0, kill: int = None, kill_after_fill: int = None, metadata: dict[str, object] | None = None, is_shadow: bool = False):
        """Initialize a limit order."""
        super().__init__(side=side, value=value, entry_price=entry_price, type=OrderType.LIMIT, leverage=leverage, kill=kill, kill_after_fill=kill_after_fill, metadata=metadata, is_shadow=is_shadow)

class MarketOrder(Order):
    """Represents a market order executed at the available market price."""

    def __init__(self, side: Side, value: Decimal, leverage: float = 1.0, metadata: dict[str, object] | None = None, is_shadow: bool = False):
        """Initialize a market order."""
        super().__init__(side=side, value=value, entry_price=None, type=OrderType.MARKET, leverage=leverage, kill=None, kill_after_fill=None, metadata=metadata, is_shadow=is_shadow)