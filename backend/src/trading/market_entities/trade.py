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
    def convert_from_order(cls, order: Order, execution_price, margin) -> Trade:
        """Create a trade from an executed order."""
        trade = cls(
            id=order.id,
            execution_price=execution_price,
            side=order.side,
            margin=margin,
            leverage=order.leverage,
            metadata=order.metadata,
            is_shadow=order.is_shadow,
        )
        return trade

    def __init__(self, id: uuid.UUID, execution_price, side: Side, margin, leverage, metadata: dict[str, object] | None = None, is_shadow: bool = False):
        """Initialize the trade with its execution and position parameters."""
        self.id = id
        self.execution_price = execution_price
        self.side = side
        self.margin = margin
        self.metadata = dict(metadata) if metadata else {}
        self.is_shadow = is_shadow
        self.invested_margin = margin
        self.closed_margin = Decimal(0)
        self.avg_close_price = Decimal(0)
        self.leverage = leverage
        self.realized_pnl = 0
        self.fees_paid = Decimal(0)
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

    def update_on_fill(self, execution_price: Decimal, margin: Decimal, leverage: Decimal):
        """Update the trade after an additional position fill."""
        total_margin = self.margin + margin
    
        self.execution_price = (
            self.execution_price * self.margin + execution_price * margin
        ) / total_margin
        self.leverage = (
            self.leverage * self.margin + leverage * margin
        ) / total_margin
        self.margin = total_margin
        self.invested_margin += margin

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
        size = self.margin * self.leverage
        return (price - self.execution_price) * self.side.value * size / self.execution_price
    
    def charge_fee(self, fee_rate: Decimal):
        """Charge a fee based on the trade's current position margin."""
        return self.charge_fee_from_margin(self.margin, fee_rate)

    def charge_fee_from_margin(self, margin, fee_rate: Decimal):
        """Charge a fee based on the specified position margin."""
        size = margin * self.leverage
        fee = size * fee_rate
        self.realized_pnl -= fee
        self.fees_paid += fee

        return fee

    def close_trade_partial(self, execuiton_price: Decimal, close_rate: Decimal):
        """Partially close the trade and realize the corresponding PnL."""
        float_pnl = self.floating_pnl_from_price(execuiton_price)

        closed_margin = self.margin * close_rate
        total_closed_margin = self.closed_margin + closed_margin
        self.avg_close_price = (
            (
                self.avg_close_price * self.closed_margin
                + execuiton_price * closed_margin
            )
            / total_closed_margin
        )
        self.closed_margin = total_closed_margin
        self.margin -= closed_margin

        realized = float_pnl * close_rate
        self.realized_pnl += realized

        return closed_margin, realized
    
    def is_active(self):
        """Return whether the trade still has an open position."""
        return self.margin > 0
    
    def close_trade(self):
        """Mark the trade as closed at the current market time."""
        self.close_time = DataProvider().get_time()