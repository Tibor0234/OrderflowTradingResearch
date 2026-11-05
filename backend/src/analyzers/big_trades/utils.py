from dataclasses import dataclass
from decimal import Decimal

from trading.market_entities.utils import Side


@dataclass(slots=True)
class BigTradeRecord:
	"""Represents a detected big trade."""
	
	time: int
	price: Decimal
	quantity: Decimal
	side: Side