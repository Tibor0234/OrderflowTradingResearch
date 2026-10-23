from __future__ import annotations
import uuid
from decimal import Decimal
from trading.market_entities.utils import Side
from trading.market_entities.order import Order
from trading.market_entities.stop_order import StopOrder
from trading.market_entities.increase_order import IncreaseOrder
from global_services.data.provider import DataProvider

class Trade:
    """Represents an active trading position and its execution state."""

    @classmethod
    def convert_from_order(cls, order: Order, execution_price, value) -> Trade:
        """Create a trade from an executed order."""
        trade = cls(
            id=order.id,
            execution_price=execution_price,
            side=order.side,
            value=value,
            leverage=order.leverage,
            metadata=order.metadata,
            is_shadow=order.is_shadow,
        )
        return trade

    def __init__(self, id: uuid.UUID, execution_price, side: Side, value, leverage, metadata: dict[str, object] | None = None, is_shadow: bool = False):
        """Initialize the trade with its execution and position parameters."""
        self.id = id
        self.execution_price = execution_price
        self.side = side
        self.value = value
        self.metadata = dict(metadata) if metadata else {}
        self.is_shadow = is_shadow
        self.invested_value = value
        self.closed_value = Decimal(0)
        self.avg_close_price = Decimal(0)
        self.leverage = leverage
        self.realized_pnl = 0
        self.open_time = DataProvider().get_time()
    
    def link(self, linked_order: IncreaseOrder | StopOrder):
        """Link an increase or stop order to this trade."""
        linked_order.set_from_source(self.id, self.side, self.is_shadow)
        return self
    
    def link_many(self, linked_orders: list[IncreaseOrder | StopOrder]):
        """Link multiple increase or stop orders to this trade."""
        if not isinstance(linked_orders, list):
            linked_orders = [linked_orders]
        
        for linked_order in linked_orders:
            self.link(linked_order)
            
        return self

    def update_on_fill(self, execution_price: Decimal, value: Decimal, leverage: Decimal):
        """Update the trade after an additional position fill."""
        total_value = self.value + value
    
        self.execution_price = (self.execution_price * self.value + execution_price * value) / total_value
        self.leverage = (self.leverage * self.value + leverage * value) / total_value
        self.value = total_value
        self.invested_value += value

    def update_metadata(self, metadata: dict[str, object]):
        """Update the trade metadata with the provided values."""
        self.metadata.update(metadata)

    @property
    def floating_pnl(self):
        """Return the unrealized profit or loss at the current market price."""
        price = DataProvider().get_price()
        return self.floating_pnl_from_price(price)

    def floating_pnl_from_price(self, price: Decimal):
        """Calculate the unrealized profit or loss at a specified price."""
        return (price - self.execution_price) * self.side.value * (self.value * self.leverage) / self.execution_price
    
    def charge_fee(self, fee_rate: Decimal):
        """Charge a fee based on the trade's current position value."""
        return self.charge_fee_from_value(self.value, fee_rate)

    def charge_fee_from_value(self, value, fee_rate: Decimal):
        """Charge a fee based on the specified position value."""
        fee = (value * self.leverage) * fee_rate
        self.realized_pnl -= fee

        return fee

    def close_trade_partial(self, execuiton_price: Decimal, close_rate: Decimal):
        """Partially close the trade and realize the corresponding PnL."""
        float_pnl = self.floating_pnl_from_price(execuiton_price)

        closed_value = self.value * close_rate
        total_closed_value = self.closed_value + closed_value
        self.avg_close_price = (
            (self.avg_close_price * self.closed_value + execuiton_price * closed_value)
            / total_closed_value
        )
        self.closed_value = total_closed_value
        self.value -= closed_value

        realized = float_pnl * close_rate
        self.realized_pnl += realized

        return closed_value, realized
    
    def is_active(self):
        """Return whether the trade still has an open position."""
        return self.value > 0
    
    def close_trade(self):
        """Mark the trade as closed at the current market time."""
        self.close_time = DataProvider().get_time()