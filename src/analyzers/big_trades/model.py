from collections import deque
from analyzers.big_trades.utils import BigTradeRecord

class BigTrades:
	"""Stores a rolling collection of detected big trades."""

	def __init__(self, length: int = 50):
		"""Initialize the rolling trade collection with a maximum length."""
		self.length = length
		self.content: deque[BigTradeRecord] = deque(maxlen=length)

	@property
	def current(self) -> BigTradeRecord | None:
		"""Return the most recent big trade, if available."""
		return self.content[-1] if self.content else None
