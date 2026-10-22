from decimal import Decimal

from trading.execution.order_book import ExecutionOrderBook
from data_managers.order_book.manager import OrderBookRow
from trading.market_entities.utils import Side


class TestExecutionOrderBook:

    def setup_method(self):
        self.book = ExecutionOrderBook()

    def test_best_bid_ask_and_spread(self):
        self.book.bids = [
            OrderBookRow(Decimal("100"), Decimal("2")),
            OrderBookRow(Decimal("99"), Decimal("5")),
        ]
        self.book.asks = [
            OrderBookRow(Decimal("101"), Decimal("3")),
            OrderBookRow(Decimal("102"), Decimal("5")),
        ]

        assert self.book.best_bid == Decimal("100")
        assert self.book.best_ask == Decimal("101")
        assert self.book.spread == Decimal("1")

    def test_market_buy_uses_ask_side(self):
        self.book.asks = [
            OrderBookRow(Decimal("100"), Decimal("2")),
        ]

        fill_price = self.book.calculate_market_fill(
            Decimal("100"),
            Decimal("1"),
            Side.BUY,
        )

        assert fill_price == Decimal("100")

    def test_market_sell_uses_bid_side(self):
        self.book.bids = [
            OrderBookRow(Decimal("100"), Decimal("2")),
        ]

        fill_price = self.book.calculate_market_fill(
            Decimal("100"),
            Decimal("1"),
            Side.SELL,
        )

        assert fill_price == Decimal("100")

    def test_market_order_consumes_multiple_levels(self):
        self.book.asks = [
            OrderBookRow(Decimal("100"), Decimal("1")),
            OrderBookRow(Decimal("101"), Decimal("1")),
        ]

        fill_price = self.book.calculate_market_fill(
            Decimal("150"),
            Decimal("1"),
            Side.BUY,
        )

        expected = Decimal("150") / (
            Decimal("1") + Decimal("50") / Decimal("101")
        )

        assert fill_price == expected

    def test_leverage_increases_executed_notional(self):
        self.book.asks = [
            OrderBookRow(Decimal("100"), Decimal("10")),
        ]

        fill_price = self.book.calculate_market_fill(
            Decimal("100"),
            Decimal("10"),
            Side.BUY,
        )

        assert fill_price == Decimal("100")

    def test_empty_book_returns_zero(self):
        fill_price = self.book.calculate_market_fill(
            Decimal("100"),
            Decimal("1"),
            Side.BUY,
        )

        assert fill_price == Decimal("0")