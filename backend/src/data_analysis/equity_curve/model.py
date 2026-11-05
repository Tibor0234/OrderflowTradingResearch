from dataclasses import dataclass, field
from decimal import Decimal

from data_analysis.utils import AnalysisType


@dataclass
class EquityCurve:
    """Stores curve identity, starting balance, recorded points, and symbol."""

    type: AnalysisType
    symbol: str | None = None
    starting_balance: Decimal | None = None
    content: dict[int, Decimal] = field(default_factory=dict)
