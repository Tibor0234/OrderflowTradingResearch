from data_managers.ohlcv.subscriber import OHLCVManagerSubscriber
from data_managers.ohlcv.utils import OHLCVMessage, OHLCVPeriod
from analyzers.ohlcv_timeframe.model import OHLCVTimeframe
from analyzers.ohlcv_timeframe.subscriber import OHLCVTimeframeSubscriber
from session_pairs.resource import Resource
from visualizers.context_chart.ohlcv_timeframe_visualizer import OHLCVTimeframeVisualizer

class OHLCVTimeframeAnalyzer(OHLCVManagerSubscriber, Resource):
    """Aggregates OHLCV candles into a selected timeframe."""

    def __init__(self, period: OHLCVPeriod):
        """Initialize the analyzer for the specified timeframe period."""
        super().__init__()
        self.model: OHLCVTimeframe = OHLCVTimeframe(period)
        self.chart_id: int | None = None
        self.visualizer: OHLCVTimeframeVisualizer | None = None
        self.setup_visualizer()

    @property
    def period(self):
        """Return the configured timeframe period."""
        return self.model.period

    def reset(self):
        """Clear the current timeframe data and reset its state."""
        self.model.interval = None
        self.model.content.clear()
        if self.visualizer is not None:
            self.visualizer.cache_current_snapshot()

    def setup_visualizer(self):
        self.visualizer = OHLCVTimeframeVisualizer(self.model, self.chart_id)

    def init_frontend(self):
        if self.visualizer is None:
            raise RuntimeError("OHLCVTimeframeAnalyzer must be initialized before frontend initialization")
        self.visualizer.init_frontend()

    def subscribe(self, subscriber: OHLCVTimeframeSubscriber):
        """Assign this timeframe's chart ID and period to a related analyzer."""
        subscriber.set_chart_id(self.chart_id, self.period)
        return self

    def process_message(self, msg: OHLCVMessage):
        """Store and visualize an OHLCV update."""
        if self.model.interval != msg.interval:
            self.model.interval = msg.interval
            self.setup_visualizer()

        self.model.content = msg.candles
        if self.visualizer is None:
            raise RuntimeError("OHLCVTimeframeAnalyzer must be initialized before receiving updates")
        self.visualizer.on_message(msg)