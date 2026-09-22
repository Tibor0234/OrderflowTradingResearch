from dash import html
from trading.market_entities.trade import Trade
from trading.market_entities.utils import Side
from visualizers.market_entity.base import MarketEntityVisualizer
from visualizers.utils import format_number, colorize_number

class TradeVisualizer(MarketEntityVisualizer):
    """Visualizes executed trades on the price chart and dashboard."""

    def __init__(self, trades: list[Trade]):
        """Initialize the visualizer with executed trades."""
        self.trades = trades

    def get_traces(self):
        """Return the Plotly traces for the executed trades."""
        return []

    def get_shapes(self):
        """Return horizontal price levels for executed trades."""
        shapes = []

        for trade in self._exclude_shadow_entities(self.trades):
            entry = float(trade.execution_price)
            is_long = trade.side == Side.BUY

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
                )
            ))

        return shapes
        
    def get_panel_content(self):
        categories = [
            "Side",
            "Value (USD)",
            "PnL (USD)",
        ]

        values = []

        for trade in self._exclude_shadow_entities(self.trades):
            side = html.Span(
                'LONG' if trade.side == Side.BUY else 'SHORT',
                style={
                    "color": "green" if trade.side == Side.BUY else "#FF5722"
                }
            )

            value_str = f"{format_number(float(trade.value))}"
            leverage_str = f"{format_number(float(trade.leverage))}"
            total_value = f"{value_str}x{leverage_str}"

            pnl_value = float(trade.realized_pnl) + float(trade.floating_pnl)

            pnl = colorize_number(pnl_value, 0)

            values.append([side, total_value, pnl])

        if not values:
            values.append([])

        return categories, values