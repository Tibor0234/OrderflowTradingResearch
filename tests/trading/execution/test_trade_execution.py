from decimal import Decimal
from unittest.mock import Mock

from trading.execution.trade_execution import TradeExecutionManager
from trading.market_entities.stop_order import (
    LiquidationOrder,
    ReduceOnly,
    StopOrder,
)
from trading.market_entities.utils import OrderType, Side


class TestTradeExecutionManager:

    def setup_method(self):
        self.position_manager = Mock()

        self.position_manager.trades = []
        self.position_manager.increase_orders = []
        self.position_manager.stop_orders = []

        self.position_manager.order_book = Mock()
        self.position_manager.order_flow = Mock()

        self.position_manager.maker_fee_rate = Decimal("0.0002")
        self.position_manager.taker_fee_rate = Decimal("0.0006")

        self.position_manager.realized_balance = Decimal("10000")
        self.position_manager.statistics = []

        self.execution = TradeExecutionManager(self.position_manager)

    def create_trade(self, side=Side.BUY):
        trade = Mock()
        trade.id = "trade-1"
        trade.side = side
        trade.execution_price = Decimal("100")
        trade.leverage = Decimal("10")
        trade.value = Decimal("1000")
        trade.is_shadow = False
        trade.is_active.return_value = True

        def link(order):
            order.set_from_source(
                trade.id,
                trade.side,
                trade.is_shadow,
            )

        trade.link.side_effect = link

        return trade

    def test_get_trade_returns_linked_trade(self):
        trade = self.create_trade()
        self.position_manager.trades.append(trade)

        order = Mock()
        order.source_id = trade.id

        result = self.execution._get_trade(order)

        assert result is trade

    def test_get_trade_returns_none_when_trade_does_not_exist(self):
        order = Mock()
        order.source_id = "unknown"

        assert self.execution._get_trade(order) is None

    def test_set_liquidation_order_creates_order(self):
        trade = self.create_trade()

        self.execution._set_liquidation_order(trade)

        assert len(self.position_manager.stop_orders) == 1

        liquidation = self.position_manager.stop_orders[0]

        assert isinstance(liquidation, LiquidationOrder)
        assert liquidation.source_id == trade.id
        assert liquidation.side == trade.side.opposite()
        assert liquidation.is_shadow == trade.is_shadow
        assert liquidation.price == Decimal("90")

    def test_set_liquidation_order_updates_existing_order(self):
        trade = self.create_trade()

        existing = LiquidationOrder(Decimal("80"))
        existing.source_id = trade.id

        self.position_manager.stop_orders.append(existing)

        self.execution._set_liquidation_order(trade)

        assert len(self.position_manager.stop_orders) == 1
        assert existing.price == Decimal("90")

    def test_stop_order_without_trade_does_nothing(self):
        stop_order = Mock()
        stop_order.source_id = "unknown"

        self.execution.on_stop_order_triggered(stop_order)

        assert self.position_manager.realized_balance == Decimal("10000")
        assert self.position_manager.trades == []

    def test_market_stop_order_closes_trade(self):
        trade = self.create_trade()
        self.position_manager.trades.append(trade)

        stop_order = ReduceOnly(pct=100)
        trade.link(stop_order)
        self.position_manager.stop_orders.append(stop_order)

        close_rate = stop_order.close_rate

        self.position_manager.order_book.calculate_market_fill.return_value = (
            Decimal("95")
        )

        trade.close_trade_partial.return_value = (
            Decimal("1000"),
            Decimal("-50"),
        )

        trade.is_active.return_value = False

        self.execution.on_stop_order_triggered(stop_order)

        self.position_manager.order_book.calculate_market_fill.assert_called_once_with(
            value=trade.value * close_rate,
            leverage=trade.leverage,
            side=stop_order.side,
        )

        trade.update_metadata.assert_called_once_with(
            stop_order.metadata,
        )

        trade.charge_fee_from_value.assert_called_once_with(
            trade.value * close_rate,
            self.position_manager.taker_fee_rate,
        )

        trade.close_trade_partial.assert_called_once_with(
            Decimal("95"),
            close_rate,
        )

        assert trade not in self.position_manager.trades
        assert stop_order not in self.position_manager.stop_orders

    def test_limit_stop_order_uses_maker_fee(self):
        trade = self.create_trade()
        self.position_manager.trades.append(trade)

        stop_order = StopOrder(
            price=Decimal("95"),
            close_rate=Decimal("0.5"),
            type=OrderType.LIMIT,
        )

        trade.link(stop_order)
        self.position_manager.stop_orders.append(stop_order)

        self.position_manager.order_flow.calculate_limit_fill.return_value = (
            Decimal("95"),
            Decimal("500"),
        )

        trade.close_trade_partial.return_value = (
            Decimal("500"),
            Decimal("-25"),
        )

        self.execution.on_stop_order_triggered(stop_order)

        self.position_manager.order_flow.calculate_limit_fill.assert_called_once_with(
            value=Decimal("500"),
            leverage=Decimal("10"),
            side=Side.SELL,
            entry_price=Decimal("95"),
        )

        trade.update_metadata.assert_called_once_with(
            stop_order.metadata,
        )

        trade.charge_fee_from_value.assert_called_once_with(
            Decimal("500"),
            self.position_manager.maker_fee_rate,
        )

        trade.close_trade_partial.assert_called_once_with(
            Decimal("95"),
            Decimal("0.5"),
        )

    def test_limit_stop_order_without_fill_does_nothing(self):
        trade = self.create_trade()
        self.position_manager.trades.append(trade)

        stop_order = StopOrder(
            price=Decimal("95"),
            close_rate=Decimal("0.5"),
            type=OrderType.LIMIT,
        )

        trade.link(stop_order)
        self.position_manager.stop_orders.append(stop_order)

        self.position_manager.order_flow.calculate_limit_fill.return_value = (
            Decimal("0"),
            Decimal("0"),
        )

        self.execution.on_stop_order_triggered(stop_order)

        trade.close_trade_partial.assert_not_called()
        assert self.position_manager.realized_balance == Decimal("10000")

    def test_partial_close_reduces_stop_order_close_rate(self):
        trade = self.create_trade()
        self.position_manager.trades.append(trade)

        stop_order = StopOrder(
            price=Decimal("95"),
            close_rate=Decimal("0.5"),
            type=OrderType.LIMIT,
        )

        trade.link(stop_order)
        self.position_manager.stop_orders.append(stop_order)

        self.position_manager.order_flow.calculate_limit_fill.return_value = (
            Decimal("95"),
            Decimal("250"),
        )

        trade.close_trade_partial.return_value = (
            Decimal("250"),
            Decimal("10"),
        )

        self.execution.on_stop_order_triggered(stop_order)

        assert stop_order.close_rate == Decimal("0.25")

    def test_full_close_finalizes_trade(self):
        trade = self.create_trade()

        self.position_manager.trades.append(trade)

        increase_order = Mock()
        increase_order.source_id = trade.id

        stop_order = Mock()
        stop_order.source_id = trade.id

        self.position_manager.increase_orders.append(increase_order)
        self.position_manager.stop_orders.append(stop_order)

        self.execution._finalize_trade(trade)

        assert trade not in self.position_manager.trades
        assert increase_order not in self.position_manager.increase_orders
        assert stop_order not in self.position_manager.stop_orders

    def test_shadow_trade_does_not_change_balance(self):
        trade = self.create_trade()
        trade.is_shadow = True

        self.position_manager.trades.append(trade)

        stop_order = ReduceOnly(pct=100)
        trade.link(stop_order)
        self.position_manager.stop_orders.append(stop_order)

        self.position_manager.order_book.calculate_market_fill.return_value = (
            Decimal("95")
        )

        trade.close_trade_partial.return_value = (
            Decimal("1000"),
            Decimal("-50"),
        )

        self.execution.on_stop_order_triggered(stop_order)

        assert self.position_manager.realized_balance == Decimal("10000")

    def test_close_expired_trades_closes_all_trades(self):
        trade = self.create_trade()
        self.position_manager.trades.append(trade)

        self.position_manager.order_book.calculate_market_fill.return_value = (
            Decimal("95")
        )

        trade.close_trade_partial.return_value = (
            Decimal("1000"),
            Decimal("50"),
        )

        trade.is_active.return_value = False

        self.execution.close_expired_trades()

        trade.close_trade_partial.assert_called_once()

        self.position_manager.order_book.calculate_market_fill.assert_called_once()

        assert trade not in self.position_manager.trades