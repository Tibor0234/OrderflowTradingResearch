from session_pairs.price_chart_resource import PriceChartResource
from data_managers.trade.subscriber import TradeManagerSubscriber
from data_managers.trade.utils import TradeMessage
from analyzers.timeframe.subscriber import TimeframeSubscriber

from analyzers.timeframe.model import Timeframe
from analyzers.timeframe.candle import Candle

from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType

class TimeframeAnalyzer(PriceChartResource, TradeManagerSubscriber):
    """Analyzes price data over a specified timeframe, generating and updating candles."""

    def __init__(self, candle_seconds=60, length=100, visualize=True, chart_slot: int | None = None):
        """Initialize the timeframe analyzer with the specified candle duration, history length, and visualization options."""
        super().__init__(chart_slot)
        self.model: Timeframe = Timeframe(length)

        self.visualize = visualize

        self.candle_seconds = candle_seconds
        self.candle_ms = candle_seconds * 1000

        self.subscribers: list[TimeframeSubscriber] = []

    @property
    def visualizer(self):
        """Return the timeframe visualizer when visualization is enabled."""
        if self.visualize:
            from visualizers.price_chart.timeframe import TimeframeVisualizer
            return TimeframeVisualizer(self.model, self.candle_seconds, self.chart_slot)
        return None

    def subscribe(self, subscriber: TimeframeSubscriber):
        """Subscribe a new subscriber to the timeframe analyzer."""
        subscriber.init_model(self.model.history.maxlen)
        subscriber.inherit_chart_slot(self.chart_slot)
        self.subscribers.append(subscriber)
        return self

    def reset(self):
        """Reset the timeframe analyzer, clearing its historical data and the current candle."""
        self.model.history.clear()
        self.model.current = None

    def process_message(self, msg: TradeMessage):
        """Update the current candle, notify subscribers, and emit a candle-close event."""
        if self.model.current is None:
            self.model.current = Candle(
                time=msg.time,
                open=msg.price
            )
        else:
            self.model.current.update_candle(msg.price)

        for sub in self.subscribers:
            sub.on_timeframe_update(msg)

        if msg.time - self.model.current.time >= self.candle_ms:
            next_open = self.model.current.time + self.candle_ms
            self.model.history.append(self.model.current)

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