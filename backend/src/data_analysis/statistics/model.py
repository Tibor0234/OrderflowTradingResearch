from dataclasses import dataclass, field
from decimal import Decimal

from data_analysis.utils import AnalysisType


@dataclass
class Statistics:
    """Stores calculated performance metrics and their scope."""

    type: AnalysisType
    symbol: str | None = None
    starting_balance: Decimal | None = None
    equity: Decimal | None = None
    total_trades: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    winrate: float | None = None
    pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    fees_paid: Decimal = field(default_factory=lambda: Decimal("0"))
    roi: Decimal = field(default_factory=lambda: Decimal("0"))
    max_drawdown: Decimal = field(default_factory=lambda: Decimal("0"))
    profit_factor: float | None = None
    expectency: float = 0
    average_win: Decimal = field(default_factory=lambda: Decimal("0"))
    average_loss: Decimal = field(default_factory=lambda: Decimal("0"))
    average_trade_duration: float | None = None
