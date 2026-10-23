from abc import ABC, abstractmethod

class PriceChartVisualizer(ABC):
    """Defines the interface for visualizing price chart data."""

    is_oscillator = False
    uses_volume_axis = False

    def __init__(self, chart_slot: int = 0):
        """Initialize the visualizer with its chart slot."""
        self.chart_slot = chart_slot

    def get_traces(self):
        """Return the Plotly traces for the visualization."""
        return []

    def get_shapes(self):
        """Return the Plotly shapes for the visualization."""
        return []