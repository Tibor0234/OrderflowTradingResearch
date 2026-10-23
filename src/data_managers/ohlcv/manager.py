from decimal import Decimal
from data_managers.ohlcv.utils import OHLCVPeriod
from data_managers.base import DataManager
from data_managers.ohlcv.subscriber import OHLCVManagerSubscriber
from data_managers.ohlcv.utils import OHLCVMessage, OHLCVCandle

class OHLCVManager(DataManager):
    """Manages OHLCV messages and forwards them to matching subscribers."""

    def __init__(self):
        """Initialize the OHLCV manager and its subscribers."""
        self.subscribers: list[OHLCVManagerSubscriber] = []

    def subscribe(self, subscriber: OHLCVManagerSubscriber):
        """Subscribe a consumer to receive OHLCV updates."""
        self.subscribers.append(subscriber)
        return self

    def forward_message(self, msg):
        """Convert a raw OHLCV message and forward it to matching subscribers."""
        conv_msg = OHLCVMessage(
            period=OHLCVPeriod(msg["period"]),
            timeframe=msg["interval"],
            candles=[
                OHLCVCandle(
                    time=int(c["open_time"]),
                    open=Decimal(c["open"]),
                    high=Decimal(c["high"]),
                    low=Decimal(c["low"]),
                    close=Decimal(c["close"]),
                    volume=Decimal(c["volume"]),
                )
                for c in msg["candles"]
            ]
        )

        for sub in self.subscribers:
            if sub.period == conv_msg.period:
                sub.process_message(conv_msg)