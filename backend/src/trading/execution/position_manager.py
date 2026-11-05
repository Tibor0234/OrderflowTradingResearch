from decimal import Decimal

from trading.execution.order_execution import OrderExecutionManager
from trading.execution.trade_execution import TradeExecutionManager
from trading.execution.order_book import ExecutionOrderBook
from trading.execution.order_flow import ExecutionOrderFlow
from trading.execution.data_analysis_handler import DataAnalysisHandler
from trading.market_entities.order import Order
from trading.market_entities.stop_order import LiquidationOrder, StopOrder
from trading.market_entities.increase_order import IncreaseOrder
from trading.market_entities.trade import Trade
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.position_panel.position_visualizer import PositionVisualizer


class PositionManager:
    """Manages orders, trades, account balance, and position execution state."""

    def __init__(
        self,
        starting_balance,
        order_book: ExecutionOrderBook,
        order_flow: ExecutionOrderFlow,
        data_analysis_handler: DataAnalysisHandler,
        maker_fee_pct=0.02,
        taker_fee_pct=0.06,
    ):
        """Initialize the position manager with execution and account configuration."""
        self.starting_balance = Decimal(starting_balance)
        self.order_book = order_book
        self.order_flow = order_flow
        self.data_analysis_handler = data_analysis_handler

        self.maker_fee_rate = Decimal(maker_fee_pct / 100)
        self.taker_fee_rate = Decimal(taker_fee_pct / 100)

        self.trades: list[Trade] = []
        self.orders: list[Order] = []
        self.increase_orders: list[IncreaseOrder] = []
        self.stop_orders: list[StopOrder] = []
        self.position_visualizer = PositionVisualizer(
            self.trades,
            self.orders,
            self.increase_orders,
            self.stop_orders,
        )

        self.order_execution = OrderExecutionManager(self)
        self.trade_execution = TradeExecutionManager(self)

        self.realized_balance = self.starting_balance

        EventBus().subscribe(EventBusMsgType.PRICE_UPDATE, self.on_price_update)
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_START, self.on_session_pair_start)
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_END, self.on_session_pair_end)
        EventBus().subscribe(EventBusMsgType.PROCESS_END, self.clear_state)

    @property
    def floating_balance(self):
        """Return the combined unrealized PnL of active trades."""
        return sum(t.floating_pnl for t in self.trades if not t.is_shadow)

    @property
    def total_balance(self):
        """Return the current account equity including realized and unrealized PnL."""
        locked_margin = sum(trade.margin for trade in self.trades if not trade.is_shadow)
        return self.realized_balance + locked_margin + self.floating_balance

    def record_trade_event(self):
        """Record a portfolio-equity boundary on every registered curve."""
        self.data_analysis_handler.record_trade_event(self.total_balance)

    def init_frontend(self):
        """Send the initial position snapshot to the frontend."""
        self.position_visualizer.init_frontend()

    def _set_liquidation_order(self, trade: Trade):
        """Set the liquidation order for a trade."""
        self.trade_execution._set_liquidation_order(trade)

    def _get_trade(self, linked_order: IncreaseOrder | StopOrder):
        """Return the trade associated with a linked order."""
        return self.trade_execution._get_trade(linked_order)

    def _is_source_open(self, linked_order: IncreaseOrder | StopOrder):
        """Return whether the source of a linked order is still open."""
        return self.trade_execution._is_source_open(linked_order)

    def remove_position_object(
        self, entity: Trade | Order | IncreaseOrder | StopOrder, notify: bool = True
    ) -> bool:
        """Remove an active position object and notify the frontend."""
        for objects in (
            self.trades,
            self.orders,
            self.increase_orders,
            self.stop_orders,
        ):
            if entity in objects:
                objects.remove(entity)
                if notify:
                    self.position_visualizer.on_removed(entity)
                return True
        return False

    def _finalize_trade(self, trade: Trade):
        """Finalize and remove a completed trade from the execution state."""
        self.trade_execution._finalize_trade(trade)

    def _finalize_order(self, order: Order):
        """Finalize and remove an order from the execution state."""
        self.order_execution._finalize_order(order)

    def _link_order_to_trade(self, order: Order, trade: Trade) -> IncreaseOrder:
        """Convert an order to an increase order and link it to a trade."""
        return self.order_execution._link_order_to_trade(order, trade)

    def on_order_triggered(self, order: Order | IncreaseOrder):
        """Execute a triggered order."""
        trade = self._get_trade(order) if isinstance(order, IncreaseOrder) else None
        if not self.order_execution.on_order_triggered(order):
            return

        if trade is None:
            if not self.trades:
                return
            trade = self.trades[-1]
        self.position_visualizer.on_update(trade)

        if isinstance(order, IncreaseOrder):
            if order in self.increase_orders:
                self.position_visualizer.on_update(order)
        else:
            for linked_order in self.increase_orders:
                if linked_order.source_id == trade.id:
                    self.position_visualizer.on_update(linked_order)

        for stop_order in self.stop_orders:
            if (
                isinstance(stop_order, LiquidationOrder)
                and stop_order.source_id == trade.id
            ):
                self.position_visualizer.on_update(stop_order)

    def on_stop_order_triggered(self, stop_order: StopOrder):
        """Execute a triggered stop order."""
        trade = self._get_trade(stop_order)
        if not self.trade_execution.on_stop_order_triggered(stop_order):
            return

        if trade is not None and trade in self.trades:
            self.position_visualizer.on_update(trade)
        if stop_order in self.stop_orders:
            self.position_visualizer.on_update(stop_order)

    def place_order(self, order: Order | IncreaseOrder | StopOrder):
        """Place an order into the appropriate execution queue."""
        self.order_execution.place_order(order)
        self.position_visualizer.on_update(order)

    def cancel_order(self, order: Order | IncreaseOrder | StopOrder):
        """Cancel an active order."""
        self.order_execution.cancel_order(order)

    def on_price_update(self):
        """Process triggered orders and update account performance on price changes."""
        equity = self.total_balance
        self.data_analysis_handler.update_on_price_change(equity)

        for order in self.orders.copy():
            if order.is_killed():
                self._finalize_order(order)
            elif order.is_triggered():
                self.on_order_triggered(order)

        if self.trades:
            for linked_order in self.increase_orders.copy() + self.stop_orders.copy():
                if linked_order.is_triggered() and self._is_source_open(linked_order):
                    if isinstance(linked_order, IncreaseOrder):
                        self.on_order_triggered(linked_order)
                    else:
                        self.on_stop_order_triggered(linked_order)

        equity = self.total_balance
        self.data_analysis_handler.update_on_price_change(equity)
        self.position_visualizer.update_trade_pnls()

    def on_session_pair_start(self):
        """Reset execution state and initialize performance tracking for a new session pair."""
        self.clear_state()
        self.data_analysis_handler.on_session_pair_start(self.total_balance)

    def on_session_pair_end(self):
        """Close expired trades and finalize session pair performance tracking."""
        self.trade_execution.close_expired_trades()
        self.data_analysis_handler.on_session_pair_end(self.total_balance)

    def clear_state(self):
        """Clear all active orders, trades, and linked execution state."""
        self.orders.clear()
        self.increase_orders.clear()
        self.stop_orders.clear()
        self.trades.clear()

        self.position_visualizer.on_clear()
