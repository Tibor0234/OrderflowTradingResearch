import plotly.graph_objects as go
from datetime import datetime
from data_analysis.equity_curve.base import BaseEquityCurve

class EquityCurveVisualizer:
    """Visualizes an equity curve with starting and latest equity levels."""

    def __init__(self, equity_curve: BaseEquityCurve):
        """Initialize the visualizer with the specified equity curve."""
        self.equity_curve = equity_curve

        self.scatter = go.Scattergl(
            x=[],
            y=[],
            mode="lines",
            line=dict(color="green", width=2),
            name="Equity Curve",
            showlegend=False
        )

    def get_traces(self):
        """Return the equity curve trace."""
        timestamps = list(self.equity_curve.content.keys())

        if timestamps:
            self.scatter.x = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]
            self.scatter.y = list(self.equity_curve.content.values())

        return self.scatter
    
    def get_shapes(self):
        """Return reference lines for starting and latest equity values."""
        shapes = []

        s_equity = self.equity_curve.starting_equity
        if s_equity is not None:
            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    x0=0,
                    x1=1,
                    yref="y",
                    y0=float(s_equity),
                    y1=float(s_equity),
                    line=dict(
                        color="rgba(255,65,0,1)",
                        width=1,
                    )
                )
            )
        
        if self.equity_curve.content:
            latest_value = list(self.equity_curve.content.values())[-1]
            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    x0=0,
                    x1=1,
                    yref="y",
                    y0=float(latest_value),
                    y1=float(latest_value),
                    line=dict(
                        color="rgba(255,255,255,1)",
                        width=1,
                        dash="dot"
                    )
                )
            )

        return shapes