from pathlib import Path

from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from report_generator.plotly_visualizers.plotly_equity_curve_visualizer import PlotlyEquityCurveVisualizer
from report_generator.plotly_visualizers.plotly_report_visualizer import PlotlyReportVisualizer
from report_generator.plotly_visualizers.plotly_statistics_visualizer import PlotlyStatisticsVisualizer
from global_services.events.utils import EventBusMsgType
from report_generator.statistics.base import BaseReportStatistics
from market_feed.utils import SessionCounter


class SessionPairBasedReportStatistics(BaseReportStatistics):
    """Generates a separate trading report for each session pair."""

    def __init__(
        self,
        report_directory: Path,
        plotly_equity_curve_visualizer: PlotlyEquityCurveVisualizer,
        plotly_statistics_visualizer: PlotlyStatisticsVisualizer,
        plotly_report_visualizer: PlotlyReportVisualizer,
        session_counter: SessionCounter,
    ):
        """Initialize the report generator and subscribe to relevant events."""
        super().__init__(
            report_directory,
            plotly_equity_curve_visualizer,
            plotly_statistics_visualizer,
            plotly_report_visualizer,
        )
        self.session_pair_start_time = None
        self.session_counter = session_counter

        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_START, self._reset_session_pair_start_time)
        EventBus().subscribe(EventBusMsgType.PRICE_UPDATE, self._capture_session_pair_start_time)
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_END, self.generate_report)

    def _get_current_time(self):
        """Return the current replay timestamp."""
        return DataProvider().get_time()

    def _reset_session_pair_start_time(self):
        """Reset the start time for the current session pair."""
        self.session_pair_start_time = None

    def _capture_session_pair_start_time(self):
        """Capture the session pair start time from the first price update."""
        if self.session_pair_start_time is None:
            self.session_pair_start_time = self._get_current_time()

    def generate_report(self):
        """Write the page PDF for the current session pair."""
        symbol = DataProvider().get_symbol()
        session_pair = self.session_counter.session_pair_count
        session = self.session_counter.session
        report_path = self.report_directory / f"session_pair_based-{session_pair}.pdf"
        self._render_pdf(
            report_path,
            f"Session {session} - {symbol}",
            self._format_time_range(self.session_pair_start_time),
            symbol=symbol,
        )
