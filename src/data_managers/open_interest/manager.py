from decimal import Decimal
from data_managers.base import DataManager
from data_managers.open_interest.subscriber import OpenInterestManagerSubscriber
from data_managers.open_interest.utils import OpenInterestMessage

class OpenInterestManager(DataManager):
    """Manages open interest messages and forwards them to subscribers."""

    def __init__(self):
        """Initialize the open interest manager and its subscribers."""
        self.subscribers: list[OpenInterestManagerSubscriber] = []

    def subscribe(self, subscriber: OpenInterestManagerSubscriber):
        """Subscribe a consumer to receive open interest updates."""
        self.subscribers.append(subscriber)
        return self

    def forward_message(self, msg):
        """Convert a raw open interest message and forward it to all subscribers."""
        conv_msg = OpenInterestMessage(
            time=int(msg["time"]),
            open_interest=Decimal(msg["openInterest"])
        )

        for sub in self.subscribers:
            sub.process_message(conv_msg)