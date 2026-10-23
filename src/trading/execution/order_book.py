from decimal import Decimal
from data_managers.order_book.manager import OrderBookManagerSubscriber, OrderBookMessage, OrderBookRow
from trading.market_entities.utils import Side

class ExecutionOrderBook(OrderBookManagerSubscriber):
    """Maintains the current order book used for trade execution simulation."""

    def __init__(self):
        """Initialize empty bid and ask levels."""
        self.bids: list[OrderBookRow] = []
        self.asks: list[OrderBookRow] = []

    def process_message(self, msg: OrderBookMessage):
        """Update the order book with the latest bid and ask levels."""
        self.bids[:] = msg.bids
        self.asks[:] = msg.asks

    @property
    def best_bid(self) -> Decimal | None:
        """Return the highest available bid price."""
        if not self.bids:
            return None
        return self.bids[0].price

    @property
    def best_ask(self) -> Decimal | None:
        """Return the lowest available ask price."""
        if not self.asks:
            return None
        return self.asks[0].price

    @property
    def spread(self) -> Decimal | None:
        """Return the current bid-ask spread."""
        if not self.bids or not self.asks:
            return None
        return self.best_ask - self.best_bid
    
    def _fill_market_order(self, value: Decimal, leverage: Decimal, book: list[OrderBookRow]) -> Decimal:
        """Calculate the volume-weighted fill price by consuming available book liquidity."""
        remaining_notional = value * leverage
        filled_quantity = Decimal(0)
        last_price = None

        for row in book:
            available_notional = row.quantity * row.price
            fill_notional = min(available_notional, remaining_notional)
            fill_qty = fill_notional / row.price
            filled_quantity += fill_qty
            remaining_notional -= fill_notional
            last_price = row.price

            if remaining_notional <= 0:
                break

        if remaining_notional > 0 and last_price is not None:
            filled_quantity += remaining_notional / last_price

        if filled_quantity == 0:
            return Decimal(0)

        return (value * leverage) / filled_quantity

    def calculate_market_fill(self, value: Decimal, leverage: Decimal, side: Side) -> Decimal:
        """Calculate the simulated fill price for a market order."""
        book_side = self.asks if side == Side.BUY else self.bids
        return self._fill_market_order(value, leverage, book_side)