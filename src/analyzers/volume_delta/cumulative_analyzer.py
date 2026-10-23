from analyzers.volume_delta.base_analyzer import BaseVolumeDeltaAnalyzer
from analyzers.big_trades.analyzer import BigTradesAnalyzer
from analyzers.utils import OscillatorRecord

class CVDAnalyzer(BaseVolumeDeltaAnalyzer):
    """Calculates cumulative volume delta from trade flow."""

    def __init__(self, big_trades: BigTradesAnalyzer | None = None, visualize=True, chart_slot: int | None = None):
        """Initialize the CVD analyzer with optional big trade filtering."""
        super().__init__(big_trades, visualize, chart_slot)

    def get_visualizer(self):
        """Return the CVD visualizer when visualization is enabled."""
        if self.visualize:
            from visualizers.price_chart.cvd import CVDVisualizer
            top_pct = (
                self.big_trades_analyzer.top_pct
                if self.big_trades_analyzer is not None
                else None
            )
            return CVDVisualizer(self.model, top_pct, self.chart_slot)
        return None

    def new_current_record(self, next_open=None):
        """Create the next CVD record while carrying forward the current value."""
        return OscillatorRecord(
            time=next_open if next_open is not None else self.model.current.time,
            value=self.model.current.value
        )