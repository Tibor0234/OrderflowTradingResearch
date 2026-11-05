from data_analysis.equity_curve.base import BaseEquityCurveAnalyzer
from data_analysis.statistics.base import BaseStatisticsAnalyzer
from trading.market_entities.trade import Trade


class DataAnalysisHandler:
    """Coordinates equity-curve and statistics updates for position execution."""

    def __init__(self):
        self.equity_curve_analyzers: list[BaseEquityCurveAnalyzer] = []
        self.statistics_analyzers: list[BaseStatisticsAnalyzer] = []

    def add_equity_curve_analyzer(self, equity_curve_analyzer: BaseEquityCurveAnalyzer):
        self.equity_curve_analyzers.append(equity_curve_analyzer)
        return self

    def add_statistics_analyzer(self, statistics_analyzer: BaseStatisticsAnalyzer):
        self.statistics_analyzers.append(statistics_analyzer)
        return self

    def update_on_price_change(self, equity):
        for equity_curve_analyzer in self.equity_curve_analyzers:
            equity_curve_analyzer.update(equity)
        for statistics_analyzer in self.statistics_analyzers:
            statistics_analyzer.observe_equity(equity)

    def record_trade_event(self, equity, closed_trade: Trade | None = None):
        for equity_curve_analyzer in self.equity_curve_analyzers:
            equity_curve_analyzer.record_trade_event(equity)
        for statistics_analyzer in self.statistics_analyzers:
            statistics_analyzer.on_trade_event(equity, closed_trade)

    def on_session_pair_start(self, starting_balance):
        """Start the preinitialized analyzers for the active symbol."""
        for equity_curve_analyzer in self.equity_curve_analyzers:
            equity_curve_analyzer.start_session_pair(starting_balance)

        for statistics_analyzer in self.statistics_analyzers:
            statistics_analyzer.start_session_pair(starting_balance)

    def on_session_pair_end(self, equity):
        for equity_curve_analyzer in self.equity_curve_analyzers:
            equity_curve_analyzer.record_session_pair_end(equity)

        for statistics_analyzer in self.statistics_analyzers:
            statistics_analyzer.on_session_pair_end(equity)
