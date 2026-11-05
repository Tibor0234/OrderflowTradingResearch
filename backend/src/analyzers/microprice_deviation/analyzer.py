from session_pairs.resource import Resource
from data_managers.order_book.utils import OrderBookMessage
from data_managers.order_book.subscriber import OrderBookManagerSubscriber
from analyzers.microprice_deviation.model import MicropriceDeviation
from analyzers.utils import OscillatorRecord

class MicropriceDeviationAnalyzer(Resource, OrderBookManagerSubscriber):
    """Calculates the deviation of the microprice from the mid-price."""

    def __init__(self, length=10):
        """Initialize the analyzer with a rolling deviation window."""
        self.model: MicropriceDeviation = MicropriceDeviation(length)

    def reset(self):
        """Clear the stored deviation records."""
        self.model.content.clear()

    def process_message(self, msg: OrderBookMessage):
        """Calculate and store the current microprice deviation."""
        best_bid_price = float(msg.bids[0].price)
        best_bid_vol = float(msg.bids[0].quantity)

        best_ask_price = float(msg.asks[0].price)
        best_ask_vol = float(msg.asks[0].quantity)

        mid = (best_bid_price + best_ask_price) * 0.5

        denom = best_bid_vol + best_ask_vol

        if denom == 0.0:
            micro = mid
        else:
            micro = (
                best_ask_price * best_bid_vol +
                best_bid_price * best_ask_vol
            ) / denom

        deviation = micro - mid

        self.model.content.append(
            OscillatorRecord(msg.time, deviation)
        )