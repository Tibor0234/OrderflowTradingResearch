from decimal import Decimal

from data_analysis.equity_curve.cumulative import CumulativeEquityCurveAnalyzer


class SymbolBasedEquityCurveAnalyzer(CumulativeEquityCurveAnalyzer):
    """Track one symbol's changes from the run balance, without early points."""

    def __init__(self, symbol: str, starting_balance: Decimal):
        super().__init__(symbol=symbol)
        starting_balance = Decimal(starting_balance)
        self.model.starting_balance = starting_balance
        self._symbol_equity = starting_balance
        self._equity_offset: Decimal | None = None

    def start_session_pair(self, starting_balance: Decimal | None = None):
        super().start_session_pair(starting_balance)
        if not self.enabled:
            self._equity_offset = None
            return
        if starting_balance is None:
            raise ValueError(
                "A symbol-based equity curve requires the portfolio equity at session start."
            )
        self._equity_offset = self._symbol_equity - starting_balance

    def update(self, equity):
        if self.enabled:
            super().update(self._to_symbol_equity(equity))

    def record_trade_event(self, equity):
        if self.enabled:
            super().record_trade_event(self._to_symbol_equity(equity))

    def record_session_pair_end(self, equity):
        if self.enabled:
            super().record_session_pair_end(self._to_symbol_equity(equity))

    def _to_symbol_equity(self, portfolio_equity: Decimal) -> Decimal:
        if self._equity_offset is None:
            raise RuntimeError(
                "Symbol-based equity must be anchored at session-pair start."
            )
        self._symbol_equity = portfolio_equity + self._equity_offset
        return self._symbol_equity
