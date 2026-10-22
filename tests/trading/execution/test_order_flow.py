from decimal import Decimal

from data_managers.trade.utils import TradeMessage
from trading.execution.order_flow import ExecutionOrderFlow
from trading.market_entities.utils import Side


class TestExecutionOrderFlow:

    def setup_method(self):
        self.order_flow = ExecutionOrderFlow()

    def test_no_trade_returns_no_fill(self):
        fill_price, filled_value = self.order_flow.calculate_limit_fill(
            value=Decimal("1000"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("0")
        assert filled_value == Decimal("0")

    def test_buy_limit_matches_sell_trade(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("99"),
                quantity=Decimal("5"),
                side=Side.SELL,
            )
        )

        fill_price, filled_value = self.order_flow.calculate_limit_fill(
            value=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("100")
        assert filled_value == Decimal("100")

    def test_sell_limit_matches_buy_trade(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("101"),
                quantity=Decimal("5"),
                side=Side.BUY,
            )
        )

        fill_price, filled_value = self.order_flow.calculate_limit_fill(
            value=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.SELL,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("100")
        assert filled_value == Decimal("100")

    def test_non_matching_trade_does_not_fill(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("101"),
                quantity=Decimal("5"),
                side=Side.SELL,
            )
        )

        fill_price, filled_value = self.order_flow.calculate_limit_fill(
            value=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("0")
        assert filled_value == Decimal("0")

    def test_fill_is_limited_by_trade_quantity(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("99"),
                quantity=Decimal("0.5"),
                side=Side.SELL,
            )
        )

        fill_price, filled_value = self.order_flow.calculate_limit_fill(
            value=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("100")
        assert filled_value == Decimal("50")
        assert self.order_flow.remaining_quantity == Decimal("0")

    def test_fill_consumes_trade_quantity(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("99"),
                quantity=Decimal("2"),
                side=Side.SELL,
            )
        )

        self.order_flow.calculate_limit_fill(
            value=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert self.order_flow.remaining_quantity == Decimal("1")

    def test_fill_is_limited_by_order_value(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("99"),
                quantity=Decimal("10"),
                side=Side.SELL,
            )
        )

        fill_price, filled_value = self.order_flow.calculate_limit_fill(
            value=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("100")
        assert filled_value == Decimal("100")
        assert self.order_flow.remaining_quantity == Decimal("9")