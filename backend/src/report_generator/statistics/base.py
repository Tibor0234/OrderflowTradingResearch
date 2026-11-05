from datetime import datetime
from pathlib import Path
from abc import abstractmethod, ABC

from report_generator.plotly_visualizers.plotly_equity_curve_visualizer import (
    PlotlyEquityCurveVisualizer,
)
from report_generator.plotly_visualizers.plotly_report_visualizer import (
    PlotlyReportVisualizer,
)
from report_generator.plotly_visualizers.plotly_statistics_visualizer import (
    PlotlyStatisticsVisualizer,
)


class BaseReportStatistics(ABC):
    """Provides shared functionality for generating trading statistics reports."""

    def __init__(
        self,
        report_directory: Path,
        plotly_equity_curve_visualizer: PlotlyEquityCurveVisualizer,
        plotly_statistics_visualizer: PlotlyStatisticsVisualizer,
        plotly_report_visualizer: PlotlyReportVisualizer,
    ):
        """Initialize the report statistics with its output and visualizers."""
        self.report_directory = report_directory
        self.plotly_equity_curve_visualizer = plotly_equity_curve_visualizer
        self.plotly_statistics_visualizer = plotly_statistics_visualizer
        self.plotly_report_visualizer = plotly_report_visualizer

    def _format_time_range(self, start_timestamp):
        """Format the report time range from the start timestamp to the current time."""
        if start_timestamp is None:
            return "Session time unavailable"

        start_time = datetime.fromtimestamp(start_timestamp / 1000)
        end_time = datetime.fromtimestamp(self._get_current_time() / 1000)
        return f"{start_time:%Y-%m-%d %H:%M:%S} - {end_time:%Y-%m-%d %H:%M:%S}"

    @abstractmethod
    def _get_current_time(self):
        """Get the current timestamp in milliseconds."""

    def _render_pdf(
        self,
        report_path,
        title,
        time_range,
        plotly_equity_curve_visualizer=None,
        plotly_statistics_visualizer=None,
        symbol=None,
    ):
        """Delegate PDF rendering to the report visualizer."""
        self.plotly_report_visualizer.render_pdf(
            report_path,
            title,
            time_range,
            (
                self.plotly_equity_curve_visualizer
                if plotly_equity_curve_visualizer is None
                else plotly_equity_curve_visualizer
            ),
            (
                self.plotly_statistics_visualizer
                if plotly_statistics_visualizer is None
                else plotly_statistics_visualizer
            ),
            symbol,
        )
