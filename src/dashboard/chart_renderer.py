import plotly.graph_objects as go
from visualizers.market_entity.base import MarketEntityVisualizer
from visualizers.price_chart.base import PriceChartVisualizer
from visualizers.context_chart.base import ContextChartVisualizer
from visualizers.data_analysis.equity_curve import EquityCurveVisualizer

class ChartRenderer:
    """Builds Plotly charts from market and analysis visualizers."""

    def build_price_chart(self, execution_visualizers: list[MarketEntityVisualizer], price_visualizers: list[PriceChartVisualizer]):
        """Build the main price chart with execution overlays and oscillator panels."""
        fig = go.Figure()
        shapes = []
        oscillators = [
            visualizer
            for visualizer in price_visualizers
            if visualizer.is_oscillator
        ][:3]
        has_volume_profile = any(
            visualizer.uses_volume_axis
            for visualizer in price_visualizers
        )

        for visualizer in execution_visualizers:
            shapes.extend(visualizer.get_shapes())

        for visualizer in price_visualizers:
            if visualizer.is_oscillator and visualizer not in oscillators:
                continue

            traces = visualizer.get_traces()
            if visualizer.is_oscillator:
                self._assign_oscillator_axis(traces, oscillators.index(visualizer) + 2)
            fig.add_traces(traces)
            shapes.extend(visualizer.get_shapes())

        fig.update_layout(
            self._price_layout(shapes, len(oscillators), has_volume_profile)
        )

        return fig

    @staticmethod
    def _assign_oscillator_axis(traces, axis_number: int):
        """Assign all traces to the specified oscillator y-axis."""
        yaxis = f"y{axis_number}"
        for trace in traces if isinstance(traces, (list, tuple)) else [traces]:
            trace.yaxis = yaxis

    def build_context_chart(self, visualizers: list[ContextChartVisualizer]):
        """Build the context chart from the provided visualizers."""
        fig = go.Figure()
        shapes = []
        has_volume_profile = any(
            getattr(visualizer, "uses_volume_axis", False)
            for visualizer in visualizers
        )

        for visualizer in visualizers:
            fig.add_traces(visualizer.get_traces())
            shapes.extend(visualizer.get_shapes())

        fig.update_layout(self._context_layout(shapes, has_volume_profile))

        return fig

    def build_equity_curve(self, visualizer: EquityCurveVisualizer):
        """Build the equity curve chart from the provided visualizer."""
        fig = go.Figure()
        shapes = []

        if visualizer:
            fig.add_traces(visualizer.get_traces())
            shapes.extend(visualizer.get_shapes())

        fig.update_layout(self._equity_layout(shapes))

        return fig

    def _base_layout(self):
        """Return the common layout configuration shared by all charts."""
        return dict(
            autosize=True,
            plot_bgcolor="black",
            paper_bgcolor="#1e1e1e",
            font=dict(color="white"),
            showlegend=True,
            margin=dict(l=0, r=0, t=10, b=0)
        )

    def _price_layout(self, shapes, oscillator_count: int, has_volume_profile: bool):
        """Build the layout for the price chart and its oscillator panels."""
        oscillator_height = 0.2 * (1.35 ** (oscillator_count - 1)) if oscillator_count else 0
        panel_height = oscillator_height / oscillator_count if oscillator_count else 0

        for panel_index in range(1, oscillator_count + 1):
            boundary = panel_index * panel_height
            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    x0=0,
                    x1=1,
                    yref="paper",
                    y0=boundary,
                    y1=boundary,
                    line=dict(
                        color="rgba(255,255,255,0.2)",
                        width=1
                    )
                )
            )

        layout = self._base_layout()

        layout.update(
            xaxis=dict(
                showgrid=False,
                gridcolor="gray",
                linecolor="white",
                rangeslider=dict(visible=False),
                domain=[0.12, 1] if has_volume_profile else [0, 1],
                anchor="y"
            ),
            yaxis=dict(
                showgrid=False,
                gridcolor="gray",
                linecolor="white",
                domain=[oscillator_height, 1],
                anchor="x",
                side="left",
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(color="white")
            ),
            shapes=shapes
        )

        if has_volume_profile:
            layout["yaxis"].update(
                anchor="free",
                position=0,
                automargin=True,
            )
            layout["xaxis2"] = dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                domain=[0, 0.12],
                anchor="y",
            )

        for panel_index in range(oscillator_count):
            axis_number = panel_index + 2
            layout[f"yaxis{axis_number}"] = dict(
                showgrid=False,
                linecolor="white",
                zeroline=False,
                domain=[panel_index * panel_height, (panel_index + 1) * panel_height],
                anchor="x",
            )

        return layout

    def _context_layout(self, shapes, has_volume_profile=False):
        """Build the layout for the context chart."""
        layout = self._base_layout()

        layout.update(
            xaxis=dict(
                showgrid=False,
                gridcolor="gray",
                linecolor="white",
                rangeslider=dict(visible=False),
                showticklabels=False,
                domain=[0.12, 1] if has_volume_profile else [0, 1],
                anchor="y",
            ),
            yaxis=dict(
                showgrid=False,
                gridcolor="gray",
                linecolor="white",
            ),
            legend=dict(
                orientation="h",
                x=0.5,
                xanchor="center",
                y=0,
                yanchor="bottom",
                font=dict(size=12),
                bgcolor="rgba(0,0,0,0)"
            ),
            shapes=shapes
        )

        if has_volume_profile:
            layout["yaxis"].update(
                anchor="free",
                position=0,
                side="left",
                automargin=True,
            )
            layout["xaxis2"] = dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                domain=[0, 0.12],
                anchor="y",
            )

        return layout

    def _equity_layout(self, shapes):
        """Build the layout for the equity curve chart."""
        layout = self._base_layout()

        layout.update(
            xaxis=dict(
                showgrid=False,
                gridcolor="gray",
                linecolor="white",
                showticklabels=False
            ),
            yaxis=dict(
                showgrid=False,
                gridcolor="gray",
                linecolor="white",
            ),
            shapes=shapes
        )

        return layout