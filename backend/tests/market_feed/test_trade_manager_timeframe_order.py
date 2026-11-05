from data_managers.trade.manager import TradeManager
from data_managers.trade.subscriber import TradeManagerSubscriber
from analyzers.timeframe.analyzer import TimeframeAnalyzer
from analyzers.timeframe.subscriber import TimeframeSubscriber


class RecordingTradeSubscriber(TradeManagerSubscriber):
    def __init__(self, events):
        self.events = events

    def process_message(self, msg):
        self.events.append(("trade", msg.time))


class RecordingTimeframeSubscriber(TimeframeSubscriber):
    def __init__(self, events):
        self.events = events

    def on_candle_close(self, next_time=None):
        self.events.append(("candle_close", next_time))


def test_trade_subscribers_process_before_timeframe_candle_close():
    events = []
    trade_manager = TradeManager()
    timeframe = TimeframeAnalyzer(candle_seconds=60)
    timeframe.subscribe(RecordingTimeframeSubscriber(events))
    trade_manager.subscribe(RecordingTradeSubscriber(events))
    trade_manager.subscribe_timeframe(timeframe)

    trade_manager.forward_message({"E": 1_000, "p": "10", "q": "1", "m": False})
    trade_manager.forward_message({"E": 61_000, "p": "11", "q": "1", "m": False})

    assert events == [
        ("trade", 1_000),
        ("trade", 61_000),
        ("candle_close", 61_000),
    ]
