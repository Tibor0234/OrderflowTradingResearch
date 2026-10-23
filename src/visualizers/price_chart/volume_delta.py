import plotly.graph_objects as go
from visualizers.price_chart.base import PriceChartVisualizer
from analyzers.volume_delta.model import VolumeDelta

class VolumeDeltaVisualizer(PriceChartVisualizer):
    """Visualizes volume delta as a directional oscillator."""

    is_oscillator = True

    def __init__(
        self,
        volume_delta_analyzer: VolumeDelta,
        big_trades_top_pct: float | None = None,
        chart_slot: int = 0,
    ):
        """Initialize the visualizer with the volume delta data and chart slot."""
        super().__init__(chart_slot)
        self.volume_delta_analyzer = volume_delta_analyzer

        name = "VD"
        if big_trades_top_pct is not None:
            name += f" (Big Trades {big_trades_top_pct:g}%)"

        self.bar = go.Bar(
            x=[],
            y=[],
            name=name,
            yaxis="y2",
        )

    def get_traces(self):
        """Return the volume delta bar trace with direction-based colors."""
        combined = list(self.volume_delta_analyzer.content)

        x_vals = [r.time for r in combined]
        y_vals = [float(r.value) for r in combined]

        colors = [
            "rgba(0, 153, 76, 1)" if y >= 0 else "rgba(200, 39, 40, 1)"
            for y in y_vals
        ]

        self.bar.x = x_vals
        self.bar.y = y_vals
        self.bar.marker = dict(color=colors)

        return self.bar