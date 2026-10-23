from decimal import Decimal

from trading.execution.order_execution import OrderExecutionManager
from trading.execution.trade_execution import TradeExecutionManager
from trading.execution.order_book import ExecutionOrderBook
from trading.execution.order_flow import ExecutionOrderFlow
from trading.market_entities.order import Order
from trading.market_entities.stop_order import StopOrder
from trading.market_entities.increase_order import IncreaseOrder
from trading.market_entities.trade import Trade
from data_analysis.equity_curve.base import BaseEquityCurve
from data_analysis.statistics.base import BaseStatistics
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType


class PositionManager:
    """Manages orders, trades, account balance, and position execution state."""

    def __init__(self, starting_balance, order_book: ExecutionOrderBook, order_flow: ExecutionOrderFlow, maker_fee_pct=0.02, taker_fee_pct=0.06):
        """Initialize the position manager with execution and account configuration."""
        self.starting_balance = Decimal(starting_balance)
        self.order_book = order_book
        self.order_flow = order_flow

        self.maker_fee_rate = Decimal(maker_fee_pct / 100)
        self.taker_fee_rate = Decimal(taker_fee_pct / 100)

        self.trades: list[Trade] = []
        self.orders: list[Order] = []
        self.increase_orders: list[IncreaseOrder] = []
        self.stop_orders: list[StopOrder] = []

        self.order_execution = OrderExecutionManager(self)
        self.trade_execution = TradeExecutionManager(self)

        self.realized_balance = self.starting_balance
        self.equity_curves: list[BaseEquityCurve] = []
        self.statistics: list[BaseStatistics] = []

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
        locked_balance = sum(trade.value for trade in self.trades if not trade.is_shadow)
        return self.realized_balance + locked_balance + self.floating_balance

    def _set_liquidation_order(self, trade: Trade):
        """Set the liquidation order for a trade."""
        self.trade_execution._set_liquidation_order(trade)

    def _get_trade(self, linked_order: IncreaseOrder | StopOrder):
        """Return the trade associated with a linked order."""
        return self.trade_execution._get_trade(linked_order)

    def _is_source_open(self, linked_order: IncreaseOrder | StopOrder):
        """Return whether the source of a linked order is still open."""
        return self.trade_execution._is_source_open(linked_order)

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
        self.order_execution.on_order_triggered(order)

    def on_stop_order_triggered(self, stop_order: StopOrder):
        """Execute a triggered stop order."""
        self.trade_execution.on_stop_order_triggered(stop_order)

    def place_order(self, order: Order | IncreaseOrder | StopOrder):
        """Place an order into the appropriate execution queue."""
        self.order_execution.place_order(order)

    def cancel_order(self, order: Order | IncreaseOrder | StopOrder):
        """Cancel an active order."""
        self.order_execution.cancel_order(order)

    def on_price_update(self):
        """Process triggered orders and update account performance on price changes."""
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

            for eq in self.equity_curves:
                eq.update(self.total_balance)

            for st in self.statistics:
                st.update_on_price_change(self.total_balance)
        else:
            for eq in self.equity_curves:
                if not eq.is_initialized():
                    eq.update(self.total_balance)

    def on_session_pair_start(self):
        """Reset execution state and initialize performance tracking for a new session pair."""
        self.clear_state()

        for eq in self.equity_curves:
            eq.start_session_pair()

        for st in self.statistics:
            st.session_pair_start(self.total_balance)

    def on_session_pair_end(self):
        """Close expired trades and finalize session pair performance tracking."""
        self.trade_execution.close_expired_trades()

        for eq in self.equity_curves:
            eq.update(self.total_balance)

        for st in self.statistics:
            st.update_on_price_change(self.total_balance, force=True)

    def clear_state(self):
        """Clear all active orders, trades, and linked execution state."""
        self.orders.clear()
        self.increase_orders.clear()
        self.stop_orders.clear()
        self.trades.clear()

    def add_equity_curve(self, equity_curve: BaseEquityCurve):
        """Register an equity curve for performance tracking."""
        self.equity_curves.append(equity_curve)
        return self

    def add_statistics(self, statistics: BaseStatistics):
        """Register a statistics tracker for performance tracking."""
        self.statistics.append(statistics)
        return self