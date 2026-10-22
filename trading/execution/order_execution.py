from decimal import Decimal

from trading.market_entities.increase_order import IncreaseOrder
from trading.market_entities.order import Order
from trading.market_entities.trade import Trade
from trading.market_entities.utils import OrderType


class OrderExecutionManager:
    """Handles order placement, cancellation, and execution against market liquidity."""

    def __init__(self, position_manager):
        """Initialize the execution manager with the position manager."""
        self.position_manager = position_manager

    @property
    def orders(self):
        """Return the currently active orders."""
        return self.position_manager.orders

    @property
    def increase_orders(self):
        """Return the currently active position increase orders."""
        return self.position_manager.increase_orders

    @property
    def stop_orders(self):
        """Return the currently active stop orders."""
        return self.position_manager.stop_orders

    @property
    def order_book(self):
        """Return the execution order book."""
        return self.position_manager.order_book

    @property
    def order_flow(self):
        """Return the order flow used for limit order execution."""
        return self.position_manager.order_flow

    @property
    def maker_fee_rate(self):
        """Return the configured maker fee rate."""
        return self.position_manager.maker_fee_rate

    @property
    def taker_fee_rate(self):
        """Return the configured taker fee rate."""
        return self.position_manager.taker_fee_rate

    def _finalize_order(self, order: Order):
        """Remove an order and all dependent orders from the execution state."""
        if order in self.orders:
            self.orders.remove(order)

        self.increase_orders[:] = [o for o in self.increase_orders if o.source_id != order.id]
        self.stop_orders[:] = [o for o in self.stop_orders if o.source_id != order.id]

    def _link_order_to_trade(self, order: Order, trade: Trade) -> IncreaseOrder:
        """Convert an order into an increase order and link it to the trade."""
        increase_order = order.convert_to_increase_order()
        self.orders.remove(order)
        trade.link(increase_order)
        self.increase_orders.append(increase_order)
        return increase_order

    def place_order(self, order: Order | IncreaseOrder):
        """Add an order to the appropriate execution queue."""
        if isinstance(order, Order):
            order.place()
            self.orders.append(order)
        elif isinstance(order, IncreaseOrder):
            self.increase_orders.append(order)
        else:
            self.stop_orders.append(order)

    def cancel_order(self, order: Order | IncreaseOrder):
        """Remove an active order from the execution queues."""
        if isinstance(order, Order):
            self._finalize_order(order)
        else:
            if order in self.increase_orders:
                self.increase_orders.remove(order)
            elif order in self.stop_orders:
                self.stop_orders.remove(order)

    def on_order_triggered(self, order: Order | IncreaseOrder):
        """Execute a triggered order, update the associated trade, and apply fees."""
        is_limit = order.type == OrderType.LIMIT

        if is_limit:
            execution_price, filled_value = self.order_flow.calculate_limit_fill(
                order.value, order.leverage, order.side, order.entry_price
            )
            if filled_value == Decimal(0):
                return
            fee_rate = self.maker_fee_rate
        else:
            execution_price = self.order_book.calculate_market_fill(
                order.value, order.leverage, order.side
            )
            filled_value = order.value
            fee_rate = self.taker_fee_rate

        if isinstance(order, IncreaseOrder):
            trade = self.position_manager.trade_execution._get_trade(order)
            if not trade:
                return

            if order.side != trade.side:
                raise ValueError("Cannot add opposite side order to existing trade")

            trade.update_on_fill(execution_price, filled_value, order.leverage)
            trade.update_metadata(order.metadata)
            fee = trade.charge_fee_from_value(filled_value, fee_rate)
        else:
            trade = Trade.convert_from_order(order, execution_price, filled_value)
            order = self._link_order_to_trade(order, trade)
            fee = trade.charge_fee(fee_rate)
            self.position_manager.trades.append(trade)

        if not trade.is_shadow:
            self.position_manager.realized_balance -= filled_value + fee

        self.position_manager.trade_execution._set_liquidation_order(trade)

        order.value -= filled_value
        if order.is_filled():
            self.increase_orders.remove(order)
        else:
            order.on_partial_fill()
