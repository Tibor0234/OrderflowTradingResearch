from session_pairs.price_chart_resource import PriceChartResource
from analyzers.timeframe.analyzer import TimeframeSubscriber
from analyzers.big_trades.analyzer import BigTradesAnalyzer
from analyzers.volume_delta.model import VolumeDelta
from data_managers.trade.utils import TradeMessage
from analyzers.utils import OscillatorRecord

class BaseVolumeDeltaAnalyzer(PriceChartResource, TimeframeSubscriber):
    """Provides the base logic for calculating volume delta."""

    def __init__(self, big_trades: BigTradesAnalyzer | None = None, visualize=True, chart_slot: int | None = None):
        """Initialize the analyzer with optional big trade filtering."""
        super().__init__(chart_slot)
        self.name: str
        self.visualize = visualize
        self.big_trades_analyzer = big_trades

        self.new_starting_value = None

    @property
    def visualizer(self):
        """Return the configured visualizer when visualization is enabled."""
        if self.visualize:
            return self.get_visualizer()
        return None

    def init_model(self, length):
        """Initialize the volume delta model with the specified window length."""
        self.model: VolumeDelta = VolumeDelta(length)

    def reset(self):
        """Clear the current and historical delta data and reset its state."""
        self.model.history.clear()
        self.model.current = None
        self.new_starting_value = None

        if self.big_trades_analyzer is not None:
            self.big_trades_analyzer.reset()

    def on_timeframe_update(self, msg: TradeMessage):
        """Process a trade and update the current volume delta."""
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
            self.model.history.append(self.model.current)

        self.model.current = self.new_current_record(next_open)

    def get_visualizer(self):
        """Return the visualizer implementation provided by the subclass."""
        raise NotImplementedError("get_visualizer must be implemented")
    
    def new_current_record(self, next_open: int | None = None):
        """Create the next current delta record using the subclass implementation."""
        raise NotImplementedError("new_current_record must be implemented")