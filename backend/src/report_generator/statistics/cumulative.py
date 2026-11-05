from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from report_generator.plotly_visualizers.plotly_equity_curve_visualizer import (
    PlotlyEquityCurveVisualizer,
)
from report_generator.plotly_visualizers.plotly_report_visualizer import (
    PlotlyReportVisualizer,
)
from report_generator.plotly_visualizers.plotly_statistics_visualizer import (
    PlotlyStatisticsVisualizer,
)
from report_generator.statistics.base import BaseReportStatistics


class CumulativeReportStatistics(BaseReportStatistics):
    """Writes the full-run and current-symbol cumulative report pages."""

    def __init__(
        self,
        report_directory,
        plotly_equity_curve_visualizer,
        plotly_statistics_visualizer,
        plotly_report_visualizer: PlotlyReportVisualizer,
        symbol_visualizers: dict[
            str,
            tuple[PlotlyEquityCurveVisualizer, PlotlyStatisticsVisualizer],
        ],
    ):
        """Initialize the report generator and subscribe to relevant events."""
        super().__init__(
            report_directory,
            plotly_equity_curve_visualizer,
            plotly_statistics_visualizer,
            plotly_report_visualizer,
        )
        self.symbol_visualizers = symbol_visualizers
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
        """Refresh full-run and current-symbol page PDFs after a session pair."""
        if self.replay_start_time is None:
            return

        symbol = DataProvider().get_symbol()
        if symbol is None:
            raise RuntimeError("Cannot create a cumulative report without an active symbol.")
        if symbol not in self.symbol_visualizers:
            raise ValueError(
                f"No cumulative report visualizers were configured for {symbol}."
            )

        self._render_pdf(
            self.report_directory / "cumulative-full_run.pdf",
            "Full Run",
            self._format_time_range(self.replay_start_time),
        )

        equity_visualizer, statistics_visualizer = self.symbol_visualizers[symbol]
        self._render_pdf(
            self.report_directory / f"cumulative-symbol-{symbol}.pdf",
            symbol,
            self._format_time_range(self.replay_start_time),
            equity_visualizer,
            statistics_visualizer,
            symbol,
        )
