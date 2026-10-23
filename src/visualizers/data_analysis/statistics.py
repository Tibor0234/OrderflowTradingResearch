from dash import html
from data_analysis.statistics.base import BaseStatistics
from visualizers.utils import colorize_number, format_number

def _format_trade_duration(seconds: float) -> str:
    """Format a duration in seconds as hours, minutes, and seconds."""
    hours = int(seconds // 3600)
    remaining_seconds = seconds % 3600
    minutes = int(remaining_seconds // 60)
    remaining_seconds = int(remaining_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

class StatisticsVisualizer:
    """Builds dashboard content from trading statistics."""

    # Maps statistic keys to their display labels and value extractors
    STAT_DEFINITIONS = {
        "total_trades": ("Total Trades", lambda s: s.total_trades),
        "trades_won": ("Trades Won", lambda s: s.trades_won),
        "trades_lost": ("Trades Lost", lambda s: s.trades_lost),
        "winrate": ("Win Rate", lambda s: colorize_number(s.winrate, min_value=0.5, is_percentage=True)),
        "roi": ("ROI", lambda s: colorize_number(s.roi, min_value=0, is_percentage=True)),
        "max_drawdown": ("Max Drawdown", lambda s: f"{s.max_drawdown:.2%}"),
        "pnl": ("PnL (USD)", lambda s: colorize_number(s.pnl, min_value=0)),
        "average_win": ("Avg Win (USD)", lambda s: format_number(s.average_win)),
        "average_loss": ("Avg Loss (USD)", lambda s: format_number(s.average_loss)),
        "expectency": ("Expectancy (USD)", lambda s: colorize_number(s.expectency, min_value=0)),
        "average_trade_duration": ("Avg Trade Duration (h:m:s)", lambda s: _format_trade_duration(s.average_trade_duration)),
    }

    DEFAULT_STATS = list(STAT_DEFINITIONS.keys())

    def __init__(self, statistics: BaseStatistics, stats: list[str] = None):
        """Initialize the visualizer with the statistics and selected metrics."""
        self.statistics = statistics
        self.stats = stats if stats is not None else self.DEFAULT_STATS

    def get_panel_content(self):
        """Return statistic labels and formatted values for the dashboard panel."""
        categories = []
        values = []
        for key in self.stats:
            label, get_value = self.STAT_DEFINITIONS[key]
            categories.append(label)
            values.append(get_value(self.statistics))

        return categories, values