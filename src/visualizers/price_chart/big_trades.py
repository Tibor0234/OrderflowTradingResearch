from datetime import datetime

import plotly.graph_objects as go

from analyzers.big_trades.model import BigTrades
from trading.market_entities.utils import Side
from visualizers.price_chart.base import PriceChartVisualizer


class BigTradesVisualizer(PriceChartVisualizer):
    """Visualizes detected big trades as price markers sized by trade quantity."""

    def __init__(self, big_trades: BigTrades, top_pct: float, chart_slot: int):
        """Initialize the visualizer with the big trade model and chart slot."""
        super().__init__(chart_slot)
        self.big_trades = big_trades
        self.top_pct = top_pct

        self.buy_markers = go.Scattergl(
            x=[],
            y=[],
            mode="markers",
            name=f"Big Trades ({top_pct:g}%)",
            marker=dict(color="#4CAF50", opacity=0.6),
            showlegend=True,
        )
        self.sell_markers = go.Scattergl(
            x=[],
            y=[],
            mode="markers",
            name=f"Big Trades ({top_pct:g}%)",
            marker=dict(color="#FF5722", opacity=0.6),
            showlegend=False,
        )

    def get_traces(self):
        """Return buy and sell markers for the detected big trades."""
        buys = []
        sells = []

        for record in self.big_trades.content:
            target = buys if record.side == Side.BUY else sells
            target.append(record)

        max_quantity = max(
            (record.quantity for record in self.big_trades.content),
            default=1,
        )

        def marker_size(record):
            return 8 + 20 * float(record.quantity / max_quantity)

        for records, trace in ((buys, self.buy_markers), (sells, self.sell_markers)):
            trace.x = [datetime.fromtimestamp(record.time / 1000) for record in records]
            trace.y = [float(record.price) for record in records]
            trace.customdata = [str(record.quantity) for record in records]
            trace.marker.size = [marker_size(record) for record in records]

        return [self.buy_markers, self.sell_markers]
