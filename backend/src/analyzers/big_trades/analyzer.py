from bisect import bisect_left, insort
from collections import deque
from decimal import Decimal
from math import ceil

from session_pairs.resource import Resource
from data_managers.trade.subscriber import TradeManagerSubscriber
from data_managers.trade.utils import TradeMessage
from analyzers.timeframe.subscriber import TimeframeSubscriber
from analyzers.big_trades.model import BigTrades
from analyzers.big_trades.utils import BigTradeRecord
from visualizers.main_chart.big_trades_visualizer import BigTradesVisualizer
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType


class BigTradesAnalyzer(Resource, TradeManagerSubscriber, TimeframeSubscriber):
	"""Identifies trades whose quantity falls within the rolling top percentage."""

	def __init__(self, length=100, sample_size=500, top_pct=5):
		"""Initialize the analyzer with a rolling trade-quantity sample."""
		super().__init__()
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
		self.chart_id: int | None = None
		self.visualizer: BigTradesVisualizer | None = None

	def bind_to_timeframe(self, _length: int, chart_id: int | None = None):
		self.chart_id = chart_id
		self.setup_visualizer()

	def setup_visualizer(self):
		self.visualizer = BigTradesVisualizer(self.model, self.chart_id, self.top_pct)

	def on_candle_close(self, next_time: int | None = None):
		if self.visualizer is None:
			raise RuntimeError("BigTradesAnalyzer must be initialized before candle updates")
		self.visualizer.on_candle_close()

	def init_frontend(self):
		if self.visualizer is None:
			raise RuntimeError("BigTradesAnalyzer must be initialized before frontend initialization")
		self.visualizer.init_frontend()

	def reset(self):
		"""Clear detected trades and reset the rolling sample."""
		self.model.content.clear()
		self._quantities.clear()
		self._sorted_quantities.clear()
		if self.visualizer is not None:
			self.visualizer.cache_current_snapshot()

	def process_message(self, msg: TradeMessage):
		"""Process a trade and emit an event when it qualifies as a big trade."""
		is_big_trade = self.is_big_trade(msg.quantity)
		if is_big_trade:
			record = BigTradeRecord(
				time=msg.time,
				price=msg.price,
				quantity=msg.quantity,
				side=msg.side,
			)
			self.model.content.append(record)

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
