from abc import ABC, abstractmethod
from decimal import Decimal

from data_analysis.statistics.model import Statistics
from data_analysis.utils import AnalysisType
from global_services.data.provider import DataProvider
from trading.market_entities.trade import Trade
from visualizers.data_analysis.statistics_visualizer import StatisticsVisualizer


class BaseStatisticsAnalyzer(ABC):
    """Calculates trading statistics and stores results in its model."""

    def __init__(
        self,
        analysis_type: AnalysisType,
        symbol: str | None = None,
    ):
        self.model = Statistics(type=analysis_type, symbol=symbol)
        self.visualizer = StatisticsVisualizer(self.model)
        self._max_equity: Decimal | None = None
        self._gross_profit = Decimal("0")
        self._gross_loss = Decimal("0")
        self.enabled = symbol is None

    def _is_enabled_for_current_session(self):
        symbol = self.model.symbol
        self.enabled = symbol is None or DataProvider().get_symbol() == symbol
        return self.enabled

    def _reset(self):
        self.model.total_trades = 0
        self.model.trades_won = 0
        self.model.trades_lost = 0
        self.model.winrate = None
        self.model.pnl = Decimal("0")
        self.model.fees_paid = Decimal("0")
        self.model.roi = Decimal("0")
        self.model.max_drawdown = Decimal("0")
        self.model.profit_factor = None
        self.model.expectency = 0
        self.model.average_win = Decimal("0")
        self.model.average_loss = Decimal("0")
        self.model.average_trade_duration = None
        self._gross_profit = Decimal("0")
        self._gross_loss = Decimal("0")

    @abstractmethod
    def start_session_pair(self, starting_balance: Decimal):
        """Enable or reset statistics for a new session pair."""

    def on_trade_event(self, equity: Decimal, closed_trade: Trade | None = None):
        """Update and publish statistics at a trade opening or closing."""
        if not self.enabled:
            return

        self._update_equity_metrics(equity)
        if closed_trade is not None:
            self._update_trade_metrics(closed_trade)

        self.visualizer.on_statistics_update()

    def observe_equity(self, equity: Decimal):
        """Track equity metrics without sending an update to the frontend."""
        if self.enabled:
            self._update_equity_metrics(equity)

    def on_session_pair_end(self, equity: Decimal):
        """Publish the final equity-based statistics for a session pair."""
        if not self.enabled:
            return

        self._update_equity_metrics(equity)
        self.visualizer.on_statistics_update()

    def _update_trade_metrics(self, trade: Trade):
        model = self.model
        pnl = trade.realized_pnl
        model.total_trades += 1
        model.pnl += pnl
        model.fees_paid += trade.fees_paid

        if pnl > 0:
            model.trades_won += 1
            self._gross_profit += pnl
            model.average_win = (
                (model.average_win * (model.trades_won - 1)) + pnl
            ) / model.trades_won
        elif pnl < 0:
            model.trades_lost += 1
            self._gross_loss += abs(pnl)
            model.average_loss = (
                (model.average_loss * (model.trades_lost - 1)) + pnl
            ) / model.trades_lost

        model.profit_factor = (
            float(self._gross_profit / self._gross_loss)
            if self._gross_loss > 0
            else None
        )
        model.winrate = model.trades_won / model.total_trades
        model.expectency = float(model.pnl / model.total_trades)

        trade_duration_s = (trade.close_time - trade.open_time) / 1000
        if model.average_trade_duration is None:
            model.average_trade_duration = trade_duration_s
        else:
            model.average_trade_duration = (
                model.average_trade_duration * (model.total_trades - 1)
                + trade_duration_s
            ) / model.total_trades

    def _update_equity_metrics(self, equity: Decimal):
        model = self.model
        model.equity = equity
        if model.starting_balance is None:
            model.starting_balance = equity
        model.roi = (equity - model.starting_balance) / model.starting_balance

        if self._max_equity is None or equity > self._max_equity:
            self._max_equity = equity
        else:
            drawdown = (self._max_equity - equity) / self._max_equity
            if drawdown > model.max_drawdown:
                model.max_drawdown = drawdown

    def init_frontend(self):
        self.visualizer.init_frontend()
