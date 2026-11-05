from decimal import Decimal

from data_analysis.statistics.cumulative import CumulativeStatisticsAnalyzer
from trading.market_entities.trade import Trade


class SymbolBasedStatisticsAnalyzer(CumulativeStatisticsAnalyzer):
    """Tracks cumulative statistics using only one symbol's equity changes."""

    def __init__(self, symbol: str, starting_balance: Decimal):
        super().__init__(symbol=symbol)
        starting_balance = Decimal(starting_balance)
        self.model.starting_balance = starting_balance
        self.model.equity = starting_balance
        self._max_equity = starting_balance
        self._symbol_equity = starting_balance
        self._equity_offset: Decimal | None = None

    def start_session_pair(self, starting_balance: Decimal):
        super().start_session_pair(starting_balance)
        if not self.enabled:
            self._equity_offset = None
            return
        self._equity_offset = self._symbol_equity - starting_balance

    def on_trade_event(self, equity: Decimal, closed_trade: Trade | None = None):
        if self.enabled:
            super().on_trade_event(self._to_symbol_equity(equity), closed_trade)

    def observe_equity(self, equity: Decimal):
        if self.enabled:
            super().observe_equity(self._to_symbol_equity(equity))

    def on_session_pair_end(self, equity: Decimal):
        if self.enabled:
            super().on_session_pair_end(self._to_symbol_equity(equity))

    def _to_symbol_equity(self, portfolio_equity: Decimal) -> Decimal:
        if self._equity_offset is None:
            raise RuntimeError(
                "Symbol-based statistics must be anchored at session-pair start."
            )
        self._symbol_equity = portfolio_equity + self._equity_offset
        return self._symbol_equity
