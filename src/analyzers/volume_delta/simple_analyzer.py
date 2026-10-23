from analyzers.volume_delta.base_analyzer import BaseVolumeDeltaAnalyzer
from analyzers.big_trades.analyzer import BigTradesAnalyzer
from analyzers.utils import OscillatorRecord
from decimal import Decimal

class VolumeDeltaAnalyzer(BaseVolumeDeltaAnalyzer):
    """Calculates volume delta for each timeframe."""

    def __init__(self, big_trades: BigTradesAnalyzer | None = None, visualize=True, chart_slot: int | None = None):
        """Initialize the volume delta analyzer with optional big trade filtering."""
        super().__init__(big_trades, visualize, chart_slot)

    def get_visualizer(self):
        """Return the volume delta visualizer when visualization is enabled."""
        if self.visualize:
            from visualizers.price_chart.volume_delta import VolumeDeltaVisualizer
            top_pct = (
                self.big_trades_analyzer.top_pct
                if self.big_trades_analyzer is not None
                else None
            )
            return VolumeDeltaVisualizer(self.model, top_pct, self.chart_slot)
        return None

    def new_current_record(self, next_open=None):
        """Create a new volume delta record with a zero starting value."""
        return OscillatorRecord(
            time=next_open if next_open is not None else 0,
            value=Decimal(0)
        )