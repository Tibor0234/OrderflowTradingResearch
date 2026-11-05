from decimal import Decimal

from data_managers.trade.subscriber import TradeManagerSubscriber
from data_managers.trade.utils import TradeMessage
from trading.market_entities.utils import Side


class ExecutionOrderFlow(TradeManagerSubscriber):
	"""Simulates limit order execution against incoming trade flow."""

	def __init__(self):
		"""Initialize the current trade and remaining executable quantity."""
		self.trade: TradeMessage | None = None
		self.remaining_quantity = Decimal(0)

	def process_message(self, msg: TradeMessage):
		"""Update the current trade flow and its remaining quantity."""
		self.trade = msg
		self.remaining_quantity = msg.quantity

	def calculate_limit_fill(self, margin: Decimal, leverage: Decimal, side: Side, entry_price: Decimal) -> tuple[Decimal, Decimal]:
		"""Calculate the fill price and margin for a matching limit order."""
		if not self.trade or self.remaining_quantity <= 0:
			return Decimal(0), Decimal(0)

		is_matching_flow = (
			(side == Side.BUY and self.trade.side == Side.SELL and self.trade.price <= entry_price)
			or (side == Side.SELL and self.trade.side == Side.BUY and self.trade.price >= entry_price)
		)
		if not is_matching_flow:
			return Decimal(0), Decimal(0)

		size = margin * leverage
		requested_quantity = size / entry_price
		fill_quantity = min(self.remaining_quantity, requested_quantity)
		is_full_fill = fill_quantity == requested_quantity
		self.remaining_quantity -= fill_quantity
		filled_margin = (
			margin
			if is_full_fill
			else (fill_quantity * entry_price) / leverage
		)
		return entry_price, filled_margin
