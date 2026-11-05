from analyzers.volume_delta.base_analyzer import BaseVolumeDeltaAnalyzer
from analyzers.big_trades.analyzer import BigTradesAnalyzer
from analyzers.utils import OscillatorRecord

class CVDAnalyzer(BaseVolumeDeltaAnalyzer):
    """Calculates cumulative volume delta from trade flow."""

    def __init__(self, big_trades: BigTradesAnalyzer | None = None):
        """Initialize the CVD analyzer with optional big trade filtering."""
        super().__init__(big_trades)

    def new_current_record(self, next_open=None):
        """Create the next CVD record while carrying forward the current value."""
        return OscillatorRecord(
            time=next_open if next_open is not None else self.model.current.time,
            value=self.model.current.value
        )

    @property
    def resource_type(self):
        return "cvd"