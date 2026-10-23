from decimal import Decimal
from data_managers.base import DataManager
from data_managers.order_book.subscriber import OrderBookManagerSubscriber
from data_managers.order_book.utils import OrderBookMessage, OrderBookRow

class OrderBookManager(DataManager):
    """Manages order book messages and forwards them to subscribers."""

    def __init__(self):
        """Initialize the order book manager and its subscribers."""
        self.subscribers: list[OrderBookManagerSubscriber] = []

    def subscribe(self, subscriber: OrderBookManagerSubscriber):
        """Subscribe a consumer to receive order book updates."""
        self.subscribers.append(subscriber)
        return self

    def forward_message(self, msg):
        """Convert a raw order book message and forward it to all subscribers."""
        conv_msg = OrderBookMessage(
            time=int(msg["E"]),
            bids=[OrderBookRow(Decimal(price), Decimal(qty)) for price, qty in (msg.get("b") or msg.get("bids") or [])],
            asks=[OrderBookRow(Decimal(price), Decimal(qty)) for price, qty in (msg.get("a") or msg.get("asks") or [])],
        )

        for sub in self.subscribers:
            sub.process_message(conv_msg)