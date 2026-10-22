from decimal import Decimal
from unittest.mock import Mock

import pytest

from trading.execution.order_execution import OrderExecutionManager
from trading.market_entities.increase_order import IncreaseLimitOrder
from trading.market_entities.order import LimitOrder, MarketOrder
from trading.market_entities.utils import Side, OrderType


class TestOrderExecutionManager:

    def setup_method(self):
        self.position_manager = Mock()

        self.position_manager.orders = []
        self.position_manager.increase_orders = []
        self.position_manager.stop_orders = []

        self.position_manager.maker_fee_rate = Decimal("0.0002")
        self.position_manager.taker_fee_rate = Decimal("0.0006")

        self.position_manager.realized_balance = Decimal("10000")
        self.position_manager.trades = []

        self.position_manager.order_book = Mock()
        self.position_manager.order_flow = Mock()
        self.position_manager.trade_execution = Mock()

        self.execution = OrderExecutionManager(self.position_manager)

    def test_place_order_adds_order_to_orders(self):
        order = MarketOrder(
            side=Side.BUY,
            value=Decimal("100"),
            leverage=Decimal("1"),
        )

        self.execution.place_order(order)

        assert order in self.position_manager.orders
        assert order.place_time is not None

    def test_place_increase_order_adds_to_increase_orders(self):
        order = IncreaseLimitOrder(
            value=Decimal("100"),
            entry_price=Decimal("100"),
            leverage=Decimal("1"),
        )

        self.execution.place_order(order)

        assert order in self.position_manager.increase_orders

    def test_cancel_order_removes_order(self):
        order = MarketOrder(
            side=Side.BUY,
            value=Decimal("100"),
            leverage=Decimal("1"),
        )

        self.position_manager.orders.append(order)

        self.execution.cancel_order(order)

        assert order not in self.position_manager.orders

    def test_cancel_order_removes_dependent_orders(self):
        order = MarketOrder(
            side=Side.BUY,
            value=Decimal("100"),
            leverage=Decimal("1"),
        )

        increase_order = Mock()
        increase_order.source_id = order.id

        stop_order = Mock()
        stop_order.source_id = order.id

        self.position_manager.orders.append(order)
        self.position_manager.increase_orders.append(increase_order)
        self.position_manager.stop_orders.append(stop_order)

        self.execution.cancel_order(order)

        assert order not in self.position_manager.orders
        assert increase_order not in self.position_manager.increase_orders
        assert stop_order not in self.position_manager.stop_orders

    def test_limit_order_without_fill_does_nothing(self):
        order = LimitOrder(
            side=Side.BUY,
            value=Decimal("100"),
            entry_price=Decimal("100"),
            leverage=Decimal("1"),
        )

        self.position_manager.orders.append(order)

        self.position_manager.order_flow.calculate_limit_fill.return_value = (
            Decimal("0"),
            Decimal("0"),
        )

        self.execution.on_order_triggered(order)

        assert self.position_manager.trades == []
        assert self.position_manager.realized_balance == Decimal("10000")
        assert order.value == Decimal("100")

    def test_limit_order_full_fill_creates_trade(self):
        order = LimitOrder(
            side=Side.BUY,
            value=Decimal("100"),
            entry_price=Decimal("100"),
            leverage=Decimal("1"),
        )

        self.position_manager.orders.append(order)

        self.position_manager.order_flow.calculate_limit_fill.return_value = (
            Decimal("100"),
            Decimal("100"),
        )

        self.execution.on_order_triggered(order)

        assert len(self.position_manager.trades) == 1

        trade = self.position_manager.trades[0]

        assert trade.side == Side.BUY
        assert trade.execution_price == Decimal("100")
        assert trade.value == Decimal("100")

        expected_fee = Decimal("100") * Decimal("0.0002")

        assert trade.realized_pnl == -expected_fee
        assert self.position_manager.realized_balance == (
            Decimal("10000") - Decimal("100") - expected_fee
        )

    def test_limit_order_partial_fill_keeps_increase_order(self):
        order = LimitOrder(
            side=Side.BUY,
            value=Decimal("100"),
            entry_price=Decimal("100"),
            leverage=Decimal("1"),
        )

        self.position_manager.orders.append(order)

        self.position_manager.order_flow.calculate_limit_fill.return_value = (
            Decimal("100"),
            Decimal("40"),
        )

        self.execution.on_order_triggered(order)

        assert len(self.position_manager.trades) == 1
        assert len(self.position_manager.increase_orders) == 1

        increase_order = self.position_manager.increase_orders[0]

        assert increase_order.value == Decimal("60")
        assert increase_order.source_id == self.position_manager.trades[0].id

    def test_market_order_uses_market_fill_and_taker_fee(self):
        order = MarketOrder(
            side=Side.BUY,
            value=Decimal("100"),
            leverage=Decimal("1"),
        )

        self.position_manager.orders.append(order)

        self.position_manager.order_book.calculate_market_fill.return_value = (
            Decimal("105")
        )

        self.execution.on_order_triggered(order)

        self.position_manager.order_book.calculate_market_fill.assert_called_once_with(
            Decimal("100"),
            Decimal("1"),
            Side.BUY,
        )

        trade = self.position_manager.trades[0]

        expected_fee = Decimal("100") * Decimal("0.0006")

        assert trade.execution_price == Decimal("105")
        assert trade.value == Decimal("100")
        assert trade.realized_pnl == -expected_fee
        assert self.position_manager.realized_balance == (
            Decimal("10000") - Decimal("100") - expected_fee
        )

    def test_increase_order_updates_existing_trade(self):
        order = IncreaseLimitOrder(
            value=Decimal("50"),
            entry_price=Decimal("100"),
            leverage=Decimal("1"),
        )
        order.set_from_source("source-id", Side.BUY, False)

        self.position_manager.increase_orders.append(order)

        trade = Mock()
        trade.side = Side.BUY
        trade.is_shadow = False
        trade.charge_fee_from_value.return_value = Decimal("0.01")

        self.position_manager.trade_execution._get_trade.return_value = trade

        self.position_manager.order_flow.calculate_limit_fill.return_value = (
            Decimal("100"),
            Decimal("50"),
        )

        self.execution.on_order_triggered(order)

        trade.update_on_fill.assert_called_once_with(
            Decimal("100"),
            Decimal("50"),
            Decimal("1"),
        )

        trade.update_metadata.assert_called_once_with(order.metadata)

        trade.charge_fee_from_value.assert_called_once_with(
            Decimal("50"),
            Decimal("0.0002"),
        )

        assert self.position_manager.realized_balance == Decimal("9949.99")
        assert order not in self.position_manager.increase_orders

    def test_increase_order_with_opposite_side_raises(self):
        order = IncreaseLimitOrder(
            value=Decimal("50"),
            entry_price=Decimal("100"),
            leverage=Decimal("1"),
        )
        order.set_from_source("source-id", Side.SELL, False)

        trade = Mock()
        trade.side = Side.BUY

        self.position_manager.trade_execution._get_trade.return_value = trade

        self.position_manager.order_flow.calculate_limit_fill.return_value = (
            Decimal("100"),
            Decimal("50"),
        )

        with pytest.raises(ValueError):
            self.execution.on_order_triggered(order)