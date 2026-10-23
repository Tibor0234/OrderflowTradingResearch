import plotly.graph_objects as go
from visualizers.price_chart.base import PriceChartVisualizer
from analyzers.volume_profile.model import VolumeProfile

class VolumeProfileVisualizer(PriceChartVisualizer):
    """Visualizes a volume profile with POC and value area levels."""

    uses_volume_axis = True

    def __init__(self, volume_profile: VolumeProfile, chart_slot: int):
        """Initialize the visualizer with the volume profile and chart slot."""
        super().__init__(chart_slot)
        self.volume_profile = volume_profile

        self.bar = go.Bar(
            x=[],
            y=[],
            orientation="h",
            name=f"VP ({self.volume_profile.length})",
            marker=dict(color="blue"),
            xaxis='x2',
            showlegend=False
        )

    def get_traces(self):
        """Return the volume profile bar trace."""
        bins = self.volume_profile.content

        self.bar.x = [(b.volume) for b in bins]
        self.bar.y = [b.low + b.size / 2 for b in bins]

        return self.bar

    def get_shapes(self):
        """Return shapes for the POC and value area boundaries."""
        shapes = []

        poc = self.volume_profile.poc
        if poc is not None:
            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    x0=0,
                    x1=1,
                    yref="y",
                    y0=poc.price,
                    y1=poc.price,
                    line=dict(
                        color="yellow",
                        width=1,
                        dash="dash"
                    )
                )
            )

        value_area = self.volume_profile.value_area
        if value_area is not None:
            shapes.append(
            dict(
                type="rect",
                xref="paper",
                yref="y",
                x0=0,
                x1=1,
                y0=value_area.low,
                y1=value_area.high,
                fillcolor="rgba(0, 0, 255, 0.1)",
                line=dict(width=0),
                )
            )
            
            shapes.append(
            dict(
                type="line",
                xref="paper",
                yref="y",
                x0=0,
                x1=1,
                y0=value_area.low,
                y1=value_area.low,
                line=dict(color="rgba(0, 0, 255, 0.5)", width=1),
                )
            )

            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    yref="y",
                    x0=0,
                    x1=1,
                    y0=value_area.high,
                    y1=value_area.high,
                    line=dict(color="rgba(0, 0, 255, 0.5)", width=1),
                )
            )

        return shapes