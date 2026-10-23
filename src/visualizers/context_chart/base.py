from abc import ABC, abstractmethod
from data_managers.ohlcv.utils import OHLCVPeriod

class ContextChartVisualizer(ABC):
    """Defines the interface for visualizing context chart data."""

    def __init__(self):
        """Initialize the visualizer with its timeframe period."""
        self.period: OHLCVPeriod

    def get_traces(self):
        """Return the Plotly traces for the visualization."""
        return []
    
    def get_shapes(self):
        """Return the Plotly shapes for the visualization."""
        return []