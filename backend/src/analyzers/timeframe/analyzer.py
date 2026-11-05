from session_pairs.resource import Resource
from data_managers.trade.subscriber import TradeManagerSubscriber
from data_managers.trade.utils import TradeMessage
from analyzers.timeframe.subscriber import TimeframeSubscriber

from analyzers.timeframe.model import Timeframe
from analyzers.timeframe.candle import Candle
from visualizers.main_chart.timeframe_visualizer import TimeframeVisualizer

from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType

class TimeframeAnalyzer(Resource, TradeManagerSubscriber):
    """Analyzes price data over a specified timeframe, generating and updating candles."""

    def __init__(self, candle_seconds=60, length=100):
        """Initialize the timeframe analyzer with the specified candle duration and history length."""
        super().__init__()
        self.model: Timeframe = Timeframe(length)

        self.candle_seconds = candle_seconds
        self.candle_ms = candle_seconds * 1000

        self.subscribers: list[TimeframeSubscriber] = []
        self.chart_id: int | None = None
        self.visualizer: TimeframeVisualizer | None = None
        self.setup_visualizer()

    def setup_visualizer(self):
        self.visualizer = TimeframeVisualizer(
            self.model,
            self.chart_id,
            self.candle_seconds,
        )

    def init_frontend(self):
        if self.visualizer is None:
            raise RuntimeError("TimeframeAnalyzer must be initialized before frontend initialization")
        self.visualizer.init_frontend()

    def subscribe(self, subscriber: TimeframeSubscriber):
        """Subscribe a new subscriber to the timeframe analyzer."""
        subscriber.bind_to_timeframe(self.model.history.maxlen, self.chart_id)
        self.subscribers.append(subscriber)
        return self

    def reset(self):
        """Reset the timeframe analyzer, clearing its historical data and the current candle."""
        self.model.history.clear()
        self.model.current = None
        if self.visualizer is not None:
            self.visualizer.cache_current_snapshot()

    def process_message(self, msg: TradeMessage):
        """Update the current candle, notify subscribers, and emit a candle-close event."""
        if self.model.current is None:
            self.model.current = Candle(
                time=msg.time,
                open=msg.price
            )
        else:
            self.model.current.update_candle(msg.price)

        if msg.time - self.model.current.time >= self.candle_ms:
            next_open = self.model.current.time + self.candle_ms
            closed_candle = self.model.current
            self.model.history.append(closed_candle)

            for sub in self.subscribers:
                sub.on_candle_close(next_open)

            self.model.current = Candle(
                time=next_open,
                open=msg.price
            )

            EventBus().emit(
                EventBusMsgType.CANDLE_CLOSE,
                self.candle_seconds
            )

            if self.visualizer is None:
                raise RuntimeError("TimeframeAnalyzer must be initialized before candle updates")
            self.visualizer.on_candle_close(closed_candle)