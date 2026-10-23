from session_pairs.resource import Resource
from data_managers.order_book.subscriber import OrderBookManagerSubscriber
from data_managers.order_book.utils import OrderBookMessage
from analyzers.order_book_imbalance.model import OrderBookImbalance
from analyzers.utils import OscillatorRecord

class BaseOrderBookImbalanceAnalyzer(Resource, OrderBookManagerSubscriber):
    """Provides the base logic for calculating weighted order book imbalance."""

    def __init__(self, depth=20, length=10):
        """Initialize the base order book imbalance analyzer with the specified depth and history length."""
        self.model: OrderBookImbalance = OrderBookImbalance(depth, length)

    def reset(self):
        """Reset the base order book imbalance analyzer, clearing its historical data."""
        self.model.content.clear()

    def process_message(self, msg: OrderBookMessage):
        """Process an incoming order book message, updating the weighted order book imbalance."""
        bids = msg.bids
        asks = msg.asks

        bid_sum = 0.0
        ask_sum = 0.0

        depth = self.model.depth

        for i in range(min(depth, len(bids))):
            bid_sum += float(bids[i].quantity) / self.get_weight(i)

        for i in range(min(depth, len(asks))):
            ask_sum += float(asks[i].quantity) / self.get_weight(i)

        denom = bid_sum + ask_sum

        if denom == 0.0:
            imb = 0.0
        else:
            imb = (bid_sum - ask_sum) / denom

        self.model.content.append(
            OscillatorRecord(msg.time, imb)
        )

    def get_weight(self, i):
        """Return the weighting factor for the given order book level."""
        raise NotImplementedError("get_weight must be implemented by subclass")