from decimal import Decimal
from data_managers.trade.utils import TradeMessage
from trading.market_entities.utils import Side
from data_managers.base import DataManager
from data_managers.trade.subscriber import TradeManagerSubscriber
from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType

class TradeManager(DataManager):
    """Manages trade messages and forwards them to subscribers."""

    def __init__(self):
        """Initialize the trade manager and its subscribers."""
        self.subscribers: list[TradeManagerSubscriber] = []

    def subscribe(self, subscriber: TradeManagerSubscriber):
        """Subscribe a consumer to receive trade updates."""
        self.subscribers.append(subscriber)
        return self

    def forward_message(self, msg):
        """Convert a raw trade message, update market state, and notify subscribers."""
        conv_msg = TradeMessage(
            time=int(msg["E"]),
            price=Decimal(msg["p"]),
            quantity=Decimal(msg["q"]),
            side=Side.SELL if msg["m"] else Side.BUY
        )

        DataProvider().set_price(conv_msg.price)
        DataProvider().set_time(conv_msg.time)
        for sub in self.subscribers:
            sub.process_message(conv_msg)

        EventBus().emit(EventBusMsgType.PRICE_UPDATE)