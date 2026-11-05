from decimal import Decimal

from session_pairs.resource import Resource
from analyzers.timeframe.subscriber import TimeframeSubscriber
from data_managers.open_interest.subscriber import OpenInterestManagerSubscriber
from data_managers.open_interest.utils import OpenInterestMessage
from analyzers.open_interest.model import OpenInterest
from analyzers.utils import OscillatorRecord
from visualizers.main_chart.open_interest_visualizer import OpenInterestVisualizer

class OpenInterestAnalyzer(Resource, OpenInterestManagerSubscriber, TimeframeSubscriber):
    """Analyzes open interest data and maintains its historical aggregation."""

    def __init__(self):
        super().__init__()
        """Initialize the open interest analyzer."""
        self._aggregation_values: list[Decimal] = []
        self._aggregation_start_time: int | None = None
        self.chart_id: int | None = None
        self.visualizer: OpenInterestVisualizer | None = None

    def bind_to_timeframe(self, length: int, chart_id: int | None = None):
        self.model = OpenInterest(length)
        self.chart_id = chart_id
        self.setup_visualizer()

    def setup_visualizer(self):
        self.visualizer = OpenInterestVisualizer(self.model, self.chart_id)

    def on_candle_close(self, next_time: int | None = None):
        if not self._aggregation_values:
            self._aggregation_start_time = next_time
            return

        aggregation_start_time = self._aggregation_start_time
        if aggregation_start_time is None:
            return

        record = OscillatorRecord(
            time=aggregation_start_time,
            value=sum(self._aggregation_values, Decimal(0)) / len(self._aggregation_values)
        )
        self.model.history.append(record)
        self._aggregation_values.clear()
        self._aggregation_start_time = next_time

        if self.visualizer is None:
            raise RuntimeError("OpenInterestAnalyzer must be initialized before candle updates")
        self.visualizer.on_candle_close(record)

    def init_frontend(self):
        if self.visualizer is None:
            raise RuntimeError("OpenInterestAnalyzer must be initialized before frontend initialization")
        self.visualizer.init_frontend()

    def reset(self):
        """Reset the open interest analyzer, clearing its history and current aggregation state."""
        self.model.history.clear()
        self.model.current = None
        self._aggregation_values.clear()
        self._aggregation_start_time = None
        if self.visualizer is not None:
            self.visualizer.cache_current_snapshot()

    def process_message(self, msg: OpenInterestMessage):
        """Process an incoming open interest message, updating the current value and aggregation history."""
        self.model.current = OscillatorRecord(
            time=msg.time,
            value=msg.open_interest
        )

        if not self._aggregation_values and self._aggregation_start_time is None:
            self._aggregation_start_time = msg.time

        self._aggregation_values.append(msg.open_interest)