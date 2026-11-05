from decimal import Decimal

from trading.market_entities.increase_order import IncreaseOrder
from trading.market_entities.stop_order import LiquidationOrder, ReduceOnlyMarket, StopOrder
from trading.market_entities.trade import Trade
from trading.market_entities.utils import OrderType
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType


class TradeExecutionManager:
    """Handles trade execution, partial closures, liquidation, and trade finalization."""
    def __init__(self, position_manager):
        """Initialize the trade execution manager with the position manager."""
        self.position_manager = position_manager

    @property
    def trades(self):
        """Return the currently active trades."""
        return self.position_manager.trades

    @property
    def increase_orders(self):
        """Return the currently active increase orders."""
        return self.position_manager.increase_orders

    @property
    def stop_orders(self):
        """Return the currently active stop orders."""
        return self.position_manager.stop_orders

    @property
    def order_book(self):
        """Return the order book associated with the position manager."""
        return self.position_manager.order_book

    @property
    def order_flow(self):
        """Return the order flow associated with the position manager."""
        return self.position_manager.order_flow

    @property
    def maker_fee_rate(self):
        """Return the maker fee rate associated with the position manager."""
        return self.position_manager.maker_fee_rate

    @property
    def taker_fee_rate(self):
        """Return the taker fee rate associated with the position manager."""
        return self.position_manager.taker_fee_rate

    def _set_liquidation_order(self, trade: Trade):
        """Create or update the liquidation order for a trade."""
        liq_price = trade.execution_price - (trade.side.value * (trade.execution_price / trade.leverage))
        for linked_order in self.stop_orders:
            if isinstance(linked_order, LiquidationOrder) and linked_order.source_id == trade.id:
                linked_order.price = liq_price
                break
        else:
            liq_order = LiquidationOrder(liq_price, metadata={"System: Exit Reason": "Liquidation"})
            trade.link(liq_order)
            self.stop_orders.append(liq_order)

    def _get_trade(self, linked_order: IncreaseOrder | StopOrder):
        """Retrieve the trade associated with a linked order."""
        return next((t for t in self.trades if t.id == linked_order.source_id), None)

    def _is_source_open(self, linked_order: IncreaseOrder | StopOrder):
        """Check if the source trade for a linked order is still open."""
        return self._get_trade(linked_order) is not None

    def _finalize_trade(self, trade: Trade):
        """Close a trade, emit its completion event, and remove linked orders."""
        if trade in self.trades:
            trade.close_trade()
            self.position_manager.remove_position_object(trade)
            EventBus().emit(EventBusMsgType.TRADE_CLOSE, trade)

            if not trade.is_shadow:
                self.position_manager.data_analysis_handler.record_trade_event(
                    self.position_manager.total_balance,
                    closed_trade=trade,
                )

        for linked_order in self.increase_orders.copy() + self.stop_orders.copy():
            if linked_order.source_id == trade.id:
                self.position_manager.remove_position_object(linked_order)

    def on_stop_order_triggered(self, stop_order: StopOrder) -> bool:
        """Execute a triggered stop order and apply the resulting trade closure."""
        trade = self._get_trade(stop_order)
        if not trade:
            return False

        is_limit = stop_order.type == OrderType.LIMIT
        order_margin = min(
            stop_order.update_remaining_close_margin(trade.margin),
            trade.margin,
        )

        if is_limit:
            execution_price, filled_margin = self.order_flow.calculate_limit_fill(
                margin=order_margin,
                leverage=trade.leverage,
                side=stop_order.side,
                entry_price=stop_order.price,
            )
            if filled_margin == Decimal(0):
                return False
            filled_close_rate = filled_margin / trade.margin
            fee_margin = filled_margin
            fee_rate = self.maker_fee_rate
        else:
            execution_price = self.order_book.calculate_market_fill(
                margin=order_margin,
                leverage=trade.leverage,
                side=stop_order.side,
            )
            filled_close_rate = order_margin / trade.margin
            fee_margin = order_margin
            fee_rate = self.taker_fee_rate

        trade.update_metadata(stop_order.metadata)
        fee = trade.charge_fee_from_margin(fee_margin, fee_rate)
        closed_margin, realized = trade.close_trade_partial(
            execution_price,
            filled_close_rate,
        )
        if not trade.is_shadow:
            self.position_manager.realized_balance += closed_margin + realized - fee

        stop_order.update_remaining_close_margin(
            trade.margin,
            filled_margin=closed_margin,
        )
        if stop_order.is_filled():
            self.position_manager.remove_position_object(stop_order)

        if not trade.is_active():
            self._finalize_trade(trade)
        return True

    def close_expired_trades(self):
        """Close all remaining trades at the end of a session pair."""
        for trade in list(self.trades):
            stop_order = ReduceOnlyMarket(close_rate=1, metadata={"System: Exit Reason": "Session End"})
            self.stop_orders.append(stop_order)
            trade.link(stop_order)
            self.on_stop_order_triggered(stop_order)
