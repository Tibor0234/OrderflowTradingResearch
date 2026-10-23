from dash import html
from trading.market_entities.order import Order
from trading.market_entities.increase_order import IncreaseOrder
from trading.market_entities.utils import Side
from visualizers.market_entity.base import MarketEntityVisualizer
from trading.market_entities.utils import OrderType
from visualizers.utils import format_number

class OrderVisualizer(MarketEntityVisualizer):
    """Visualizes active limit and increase orders on the price chart and dashboard."""

    def __init__(self, orders: list[Order], increase_orders: list[IncreaseOrder]):
        """Initialize the visualizer with active orders."""
        self.orders = orders
        self.increase_orders = increase_orders

    def get_shapes(self):
        """Return horizontal price levels for active limit orders."""
        shapes = []

        for order in self._exclude_shadow_entities(self.orders + self.increase_orders):
            if order.type == OrderType.MARKET:
                continue

            entry = float(order.entry_price)
            is_long = order.side == Side.BUY

            # ---- ENTRY VONAL PAPER KOORDINÁTÁKKAL ----
            shapes.append(dict(
                type="line",
                xref="paper",
                yref="y",
                x0=0,
                x1=1,
                y0=entry,
                y1=entry,
                line=dict(
                    color="#4CAF50" if is_long else "#FF5722",
                    width=2,
                    dash="dash"
                )
            ))

        return shapes
        
    def get_panel_content(self):
        """Return order details formatted for the dashboard panel."""
        categories = [
            "Side",
            "Value (USD)",
            "Entry Price"
        ]

        values = []

        for order in self._exclude_shadow_entities(self.orders + self.increase_orders):
            if order.type == OrderType.MARKET:
                continue

            side = html.Span(
                'BUY' if order.side == Side.BUY else 'SELL',
                style={
                    "color": "green" if order.side == Side.BUY else "#FF5722"
                }
            )

            value_str = f"{format_number(float(order.value))}"
            leverage_str = f"{format_number(float(order.leverage))}"
            total_value = f"{value_str}x{leverage_str}"

            entry_price = float(order.entry_price)
            pnl = format_number(float(f"{entry_price:.2f}"))

            values.append([side, total_value, pnl])

        if not values:
            values.append([])

        return categories, values