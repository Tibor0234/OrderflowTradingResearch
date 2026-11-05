from session_pairs.resource import Resource
from analyzers.timeframe.subscriber import TimeframeSubscriber
from data_managers.trade.subscriber import TradeManagerSubscriber
from analyzers.big_trades.analyzer import BigTradesAnalyzer
from analyzers.volume_delta.model import VolumeDelta
from data_managers.trade.utils import TradeMessage
from analyzers.utils import OscillatorRecord
from visualizers.main_chart.volume_delta_visualizer import VolumeDeltaVisualizer

class BaseVolumeDeltaAnalyzer(Resource, TimeframeSubscriber, TradeManagerSubscriber):
    """Provides the base logic for calculating volume delta."""

    def __init__(self, big_trades: BigTradesAnalyzer | None = None):
        """Initialize the analyzer with optional big trade filtering."""
        super().__init__()
        self.big_trades_analyzer = big_trades
        self.chart_id: int | None = None
        self.visualizer: VolumeDeltaVisualizer | None = None

        self.new_starting_value = None

    def setup_visualizer(self):
        self.visualizer = VolumeDeltaVisualizer(
            self.model,
            self.chart_id,
            self.resource_type,
            self.big_trades_analyzer,
        )

    def init_frontend(self):
        if self.visualizer is None:
            raise RuntimeError("Volume delta analyzer must be initialized before frontend initialization")
        self.visualizer.init_frontend()

    def bind_to_timeframe(self, length: int, chart_id: int | None = None):
        """Bind the model to its source timeframe and chart context."""
        self.model: VolumeDelta = VolumeDelta(length)
        self.chart_id = chart_id
        self.setup_visualizer()

    def reset(self):
        """Clear the current and historical delta data and reset its state."""
        self.model.history.clear()
        self.model.current = None
        self.new_starting_value = None

        if self.big_trades_analyzer is not None:
            self.big_trades_analyzer.reset()
        if self.visualizer is not None:
            self.visualizer.cache_current_snapshot()

    def process_message(self, msg: TradeMessage):
        """Process a manager trade update and update the current volume delta."""
        if self.model.current is None:
            self.model.current = OscillatorRecord(
                time=msg.time,
                value=self.new_starting_value if self.new_starting_value is not None else 0
            )

        if self.big_trades_analyzer is not None:
            is_big_trade = self.big_trades_analyzer.process_message(msg)
            if not is_big_trade:
                return

        delta = msg.quantity * msg.side.value
        self.model.current.value += delta

    def on_candle_close(self, next_open: int | None = None):
        """Store the current delta and initialize the next record."""
        if self.model.current is not None:
            closed_record = self.model.current
            self.model.history.append(closed_record)
            if self.visualizer is None:
                raise RuntimeError("Volume delta analyzer must be initialized before candle updates")
            self.visualizer.on_candle_close(closed_record)

        self.model.current = self.new_current_record(next_open)

    def new_current_record(self, next_open: int | None = None):
        """Create the next current delta record using the subclass implementation."""
        raise NotImplementedError("new_current_record must be implemented")

    @property
    def resource_type(self):
        raise NotImplementedError("resource_type must be implemented")