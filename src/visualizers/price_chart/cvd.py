import plotly.graph_objects as go
from visualizers.price_chart.base import PriceChartVisualizer
from analyzers.volume_delta.model import VolumeDelta

class CVDVisualizer(PriceChartVisualizer):
    """Visualizes cumulative volume delta as an oscillator."""

    is_oscillator = True

    def __init__(
        self,
        cvd_analyzer: VolumeDelta,
        big_trades_top_pct: float | None = None,
        chart_slot: int = 0,
    ):
        """Initialize the visualizer with the CVD data and chart slot."""
        super().__init__(chart_slot)
        self.cvd_analyzer = cvd_analyzer

        name = "CVD"
        if big_trades_top_pct is not None:
            name += f" (Big Trades {big_trades_top_pct:g}%)"

        self.scatter = go.Scattergl(
            x=[],
            y=[],
            mode="lines",
            name=name,
            yaxis="y2",
            line=dict(color="gray", width=1),
        )

    def get_traces(self):
        """Return the CVD trace with direction-based marker colors."""
        combined = list(self.cvd_analyzer.content)

        x_vals = [r.time for r in combined]
        y_vals = [float(r.value) for r in combined]

        colors = [
            "rgba(0, 153, 76, 1)" if y >= 0 else "rgba(200, 39, 40, 1)"
            for y in y_vals
        ]

        self.scatter.x = x_vals
        self.scatter.y = y_vals
        self.scatter.mode = "lines+markers"
        self.scatter.marker = dict(color=colors)

        return self.scatter