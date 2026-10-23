from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from report_generator.base import BaseReportGenerator


class CumulativeReportGenerator(BaseReportGenerator):
    """Generates a cumulative trading report across all session pairs."""

    def __init__(self, report_directory):
        """Initialize the report generator and subscribe to relevant events."""
        super().__init__(report_directory)
        self.replay_start_time = None

        EventBus().subscribe(EventBusMsgType.PRICE_UPDATE, self._capture_replay_start_time)
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_END, self.generate_report)

    def _get_current_time(self):
        """Return the current replay timestamp."""
        return DataProvider().get_time()

    def _capture_replay_start_time(self):
        """Capture the replay start time from the first price update."""
        if self.replay_start_time is None:
            self.replay_start_time = self._get_current_time()

    def generate_report(self):
        """Generate the cumulative report when the replay session ends."""
        if self.replay_start_time is None:
            return

        self._render_pdf(
            self.report_directory / "summary.pdf",
            "Summary",
            self._format_time_range(self.replay_start_time),
            self.equity_visualizer,
            self.statistics_visualizer,
        )

    def set_visualizers(self, equity_visualizer, statistics_visualizer):
        """Set the visualizers used to generate the report."""
        self.equity_visualizer = equity_visualizer
        self.statistics_visualizer = statistics_visualizer
        return self