from data_managers.ohlcv.subscriber import OHLCVManagerSubscriber
from data_managers.ohlcv.utils import OHLCVMessage, OHLCVPeriod
from analyzers.ohlcv_timeframe.subscriber import OHLCVTimeframeSubscriber
from analyzers.ohlcv_timeframe.model import OHLCVTimeframe
from session_pairs.resource import Resource

class OHLCVTimeframeAnalyzer(OHLCVManagerSubscriber, Resource):
    """Aggregates OHLCV candles into a selected timeframe."""

    def __init__(self, period: OHLCVPeriod, visualize=True):
        """Initialize the analyzer for the specified timeframe period."""
        self.model: OHLCVTimeframe = OHLCVTimeframe(period)

        self.visualize = visualize
        self.subscribers: list[OHLCVTimeframeSubscriber] = []

    @property
    def period(self):
        """Return the configured timeframe period."""
        return self.model.period

    @property
    def visualizer(self):
        """Return the timeframe visualizer when visualization is enabled."""
        if self.visualize:
            from visualizers.context_chart.timeframe import OHLCVTimeframeVisualizer
            return OHLCVTimeframeVisualizer(self.model)
        return None

    def reset(self):
        """Clear the current timeframe data and reset its state."""
        self.model.timeframe = None
        self.model.content.clear()

    def process_message(self, msg: OHLCVMessage):
        """Process an OHLCV update and notify subscribed consumers."""
        if self.model.timeframe is None:
            self.model.timeframe = msg.timeframe

        if not self.model.content:
            self.model.content = msg.candles

        for sub in self.subscribers:
            sub.on_ohlcv_timeframe_update(msg)

    def subscribe(self, subscriber: OHLCVTimeframeSubscriber):
        """Subscribe a consumer to timeframe updates."""
        self.subscribers.append(subscriber)
        subscriber.set_period(self.model.period)
        return self