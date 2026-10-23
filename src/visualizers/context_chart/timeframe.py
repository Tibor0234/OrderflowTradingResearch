from datetime import datetime
import plotly.graph_objects as go
from analyzers.ohlcv_timeframe.model import OHLCVTimeframe
from visualizers.context_chart.base import ContextChartVisualizer

class OHLCVTimeframeVisualizer(ContextChartVisualizer):
    """Visualizes OHLCV candles for a specific timeframe."""

    def __init__(self, timeframe: OHLCVTimeframe):
        """Initialize the visualizer with the specified timeframe."""
        self.timeframe = timeframe
        self.period = timeframe.period

        self.candlestick = self.candlestick = go.Candlestick(
            x=[],
            open=[],
            high=[],
            low=[],
            close=[],
            showlegend=False
        )

    def get_traces(self):
        """Return the current OHLCV candlestick trace."""
        candles = self.timeframe.content

        if not candles: return []

        self.candlestick.x = [datetime.fromtimestamp(c.time / 1000) for c in candles]
        self.candlestick.open = [c.open for c in candles]
        self.candlestick.high = [c.high for c in candles]
        self.candlestick.low = [c.low for c in candles]
        self.candlestick.close = [c.close for c in candles]

        return self.candlestick