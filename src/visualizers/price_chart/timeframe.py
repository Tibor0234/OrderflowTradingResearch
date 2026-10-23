from datetime import datetime
import plotly.graph_objects as go
from analyzers.timeframe.model import Timeframe
from visualizers.price_chart.base import PriceChartVisualizer
from global_services.data.provider import DataProvider

class TimeframeVisualizer(PriceChartVisualizer):
    """Visualizes timeframe candles and the current market price."""

    def __init__(self, timeframe: Timeframe, candle_seconds: int, chart_slot: int):
        """Initialize the visualizer with the timeframe and chart slot."""
        super().__init__(chart_slot)
        self.timeframe = timeframe
        self.candle_seconds = candle_seconds

        self.candlestick = go.Candlestick(
            x=[],
            open=[],
            high=[],
            low=[],
            close=[],
            name="",
        )

    def get_traces(self):
        """Return the timeframe candlestick trace."""
        combined = list(self.timeframe.content)

        self.candlestick.x = [datetime.fromtimestamp(c.time / 1000) for c in combined]
        self.candlestick.open = [c.open for c in combined]
        self.candlestick.high = [c.high for c in combined]
        self.candlestick.low = [c.low for c in combined]
        self.candlestick.close = [c.close for c in combined]
        self.candlestick.name=f'{DataProvider().get_symbol()} ({self.candle_seconds}s)'

        return self.candlestick
    
    def get_shapes(self):
        """Return a horizontal line marking the current market price."""
        current_price = DataProvider().get_price()
        if current_price is None:
            return []
        
        return [
            dict(
                type="line",
                xref="paper",
                x0=0,
                x1=1,
                yref="y",
                y0=float(current_price),
                y1=float(current_price),
                line=dict(
                    color="rgba(255,255,255,1)",
                    width=1,
                    dash="dot"
                )
            )
        ]