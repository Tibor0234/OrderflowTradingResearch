from bisect import bisect_left, insort
from collections import deque
from decimal import Decimal
from math import ceil

from session_pairs.price_chart_resource import PriceChartResource
from data_managers.trade.subscriber import TradeManagerSubscriber
from data_managers.trade.utils import TradeMessage
from analyzers.big_trades.model import BigTrades
from analyzers.big_trades.utils import BigTradeRecord
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType


class BigTradesAnalyzer(PriceChartResource, TradeManagerSubscriber):
	"""Identifies trades whose quantity falls within the rolling top percentage."""

	def __init__(self, length=100, sample_size=500, top_pct=5, visualize=True, chart_slot: int | None = None):
		"""Initialize the analyzer with a rolling trade-quantity sample."""
		super().__init__(chart_slot)
		if length < 1:
			raise ValueError("length must be at least 1")
		if sample_size < 1:
			raise ValueError("sample_size must be at least 1")
		if not 0 < top_pct <= 100:
			raise ValueError("top_pct must be between 0 and 100")

		self.model: BigTrades = BigTrades(length)
		self.sample_size = sample_size
		self.top_pct = top_pct
		self.top_rate = Decimal(str(top_pct)) / Decimal(100)
		self._quantities: deque[Decimal] = deque(maxlen=sample_size)
		self._sorted_quantities: list[Decimal] = []

		self.visualize = visualize

	@property
	def visualizer(self):
		"""Return the big-trade visualizer when visualization is enabled."""
		if self.visualize:
			from visualizers.price_chart.big_trades import BigTradesVisualizer
			return BigTradesVisualizer(self.model, self.top_pct, self.chart_slot)
		return None

	def reset(self):
		"""Clear detected trades and reset the rolling sample."""
		self.model.content.clear()
		self._quantities.clear()
		self._sorted_quantities.clear()

	def process_message(self, msg: TradeMessage):
		"""Process a trade and emit an event when it qualifies as a big trade."""
		is_big_trade = self.is_big_trade(msg.quantity)
		if is_big_trade:
			self.model.content.append(BigTradeRecord(
				time=msg.time,
				price=msg.price,
				quantity=msg.quantity,
				side=msg.side,
			))

			EventBus().emit(EventBusMsgType.BIG_TRADE, msg, self.top_rate)

		self._add_quantity(msg.quantity)

		return is_big_trade

	def _add_quantity(self, quantity: Decimal):
		"""Add a quantity to the rolling sample while maintaining sorted order."""
		if len(self._quantities) == self.sample_size:
			expired_quantity = self._quantities.popleft()
			expired_index = bisect_left(self._sorted_quantities, expired_quantity)
			self._sorted_quantities.pop(expired_index)

		self._quantities.append(quantity)
		insort(self._sorted_quantities, quantity)

	def is_big_trade(self, quantity: Decimal) -> bool:
		"""Returns whether quantity is in the rolling top volume range."""
		if not self._quantities:
			return False

		rank = ceil((1 - self.top_rate) * len(self._sorted_quantities))
		threshold = self._sorted_quantities[max(0, rank - 1)]			

		return quantity >= threshold
