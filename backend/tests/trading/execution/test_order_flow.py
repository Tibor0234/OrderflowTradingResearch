from decimal import Decimal

from data_managers.trade.utils import TradeMessage
from trading.execution.order_flow import ExecutionOrderFlow
from trading.market_entities.utils import Side


class TestExecutionOrderFlow:

    def setup_method(self):
        self.order_flow = ExecutionOrderFlow()

    def test_no_trade_returns_no_fill(self):
        fill_price, filled_margin = self.order_flow.calculate_limit_fill(
            margin=Decimal("1000"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("0")
        assert filled_margin == Decimal("0")

    def test_buy_limit_matches_sell_trade(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("99"),
                quantity=Decimal("5"),
                side=Side.SELL,
            )
        )

        fill_price, filled_margin = self.order_flow.calculate_limit_fill(
            margin=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("100")
        assert filled_margin == Decimal("100")

    def test_sell_limit_matches_buy_trade(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("101"),
                quantity=Decimal("5"),
                side=Side.BUY,
            )
        )

        fill_price, filled_margin = self.order_flow.calculate_limit_fill(
            margin=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.SELL,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("100")
        assert filled_margin == Decimal("100")

    def test_non_matching_trade_does_not_fill(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("101"),
                quantity=Decimal("5"),
                side=Side.SELL,
            )
        )

        fill_price, filled_margin = self.order_flow.calculate_limit_fill(
            margin=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("0")
        assert filled_margin == Decimal("0")

    def test_fill_is_limited_by_trade_quantity(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("99"),
                quantity=Decimal("0.5"),
                side=Side.SELL,
            )
        )

        fill_price, filled_margin = self.order_flow.calculate_limit_fill(
            margin=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("100")
        assert filled_margin == Decimal("50")
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
            margin=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert self.order_flow.remaining_quantity == Decimal("1")

    def test_fill_is_limited_by_order_margin(self):
        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=Decimal("99"),
                quantity=Decimal("10"),
                side=Side.SELL,
            )
        )

        fill_price, filled_margin = self.order_flow.calculate_limit_fill(
            margin=Decimal("100"),
            leverage=Decimal("1"),
            side=Side.BUY,
            entry_price=Decimal("100"),
        )

        assert fill_price == Decimal("100")
        assert filled_margin == Decimal("100")
        assert self.order_flow.remaining_quantity == Decimal("9")

    def test_full_fill_returns_exact_order_margin_without_rounding_drift(self):
        order_margin = Decimal("1000")
        leverage = Decimal("10")
        entry_price = Decimal("3")
        trade_quantity = Decimal("4000")

        self.order_flow.process_message(
            TradeMessage(
                time=0,
                price=entry_price,
                quantity=trade_quantity,
                side=Side.SELL,
            )
        )

        fill_price, filled_margin = self.order_flow.calculate_limit_fill(
            margin=order_margin,
            leverage=leverage,
            side=Side.BUY,
            entry_price=entry_price,
        )

        requested_size = order_margin * leverage
        requested_quantity = requested_size / entry_price
        assert fill_price == entry_price
        assert filled_margin == order_margin
        assert self.order_flow.remaining_quantity == trade_quantity - requested_quantity