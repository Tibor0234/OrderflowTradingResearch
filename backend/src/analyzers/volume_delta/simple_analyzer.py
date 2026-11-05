from analyzers.volume_delta.base_analyzer import BaseVolumeDeltaAnalyzer
from analyzers.big_trades.analyzer import BigTradesAnalyzer
from analyzers.utils import OscillatorRecord
from decimal import Decimal

class VolumeDeltaAnalyzer(BaseVolumeDeltaAnalyzer):
    """Calculates volume delta for each timeframe."""

    def __init__(self, big_trades: BigTradesAnalyzer | None = None):
        """Initialize the volume delta analyzer with optional big trade filtering."""
        super().__init__(big_trades)

    def new_current_record(self, next_open=None):
        """Create a new volume delta record with a zero starting value."""
        return OscillatorRecord(
            time=next_open if next_open is not None else 0,
            value=Decimal(0)
        )

    @property
    def resource_type(self):
        return "volume_delta"