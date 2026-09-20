import logging

import dash
from dash import Input, Output
from dashboard.chart_renderer import ChartRenderer
from dashboard.dashboard_layout import DashboardLayout
from dashboard.panel_content_renderer import PanelContentRenderer
from data_managers.ohlcv.utils import OHLCVPeriod
from visualizers.news_panel.news import NewsVisualizer
from visualizers.price_chart.base import PriceChartVisualizer
from visualizers.context_chart.base import ContextChartVisualizer
from visualizers.market_entity.trade import TradeVisualizer
from visualizers.market_entity.order import OrderVisualizer
from visualizers.market_entity.stop_order import StopOrderVisualizer
from visualizers.data_analysis.statistics import StatisticsVisualizer
from visualizers.data_analysis.equity_curve import EquityCurveVisualizer
from market_feed.utils import SessionCounter

class LiveDashboard:
    """Manages the live Dash application and its dashboard visualizers."""

    def __init__(self, title):
        """Initialize the dashboard, its components, and callbacks."""
        self.app = dash.Dash(__name__)
        self.app.title = title

        self.layout = DashboardLayout()
        self.chart_renderer = ChartRenderer()
        self.panel_content_renderer = PanelContentRenderer()

        self.price_visualizers = []
        self.price_chart_count = 1
        self.context_visualizers = {
            OHLCVPeriod.LAST_DAY: [],
            OHLCVPeriod.LAST_WEEK: []
        }

        self.news_visualizer = None

        self.trade_visualizer = None
        self.order_visualizer = None
        self.stop_order_visualizer = None

        self.session_counter = None

        self.session_pair_equity_visualizer = None
        self.cumulative_equity_visualizer = None

        self.session_pair_statistics_visualizer = None
        self.cumulative_statistics_visualizer = None

        self.app.layout = self.layout.build(self.price_chart_count)
        self._register_callbacks()

    def _build_dashboard_snapshot(self):
        """Build the current chart figures and panel contents."""
        figures = {
            "Price chart 0": self.chart_renderer.build_price_chart(
                [self.trade_visualizer, self.order_visualizer, self.stop_order_visualizer],
                self._get_price_visualizers(0)
            ),
            "Price chart 1": self.chart_renderer.build_price_chart(
                [self.trade_visualizer, self.order_visualizer, self.stop_order_visualizer],
                self._get_price_visualizers(1)
            ),
            "Last week chart": self.chart_renderer.build_context_chart(
                self.context_visualizers[OHLCVPeriod.LAST_WEEK]
            ),
            "Last day chart": self.chart_renderer.build_context_chart(
                self.context_visualizers[OHLCVPeriod.LAST_DAY]
            ),
            "Session pair equity curve": self.chart_renderer.build_equity_curve(
                self.session_pair_equity_visualizer
            ),
            "Cumulative equity curve": self.chart_renderer.build_equity_curve(
                self.cumulative_equity_visualizer
            )
        }

        panels = {
            "Session pair": self.panel_content_renderer.render_session_pair_panel(
                self.session_counter
            ),
            "Trades": self.panel_content_renderer.render_execution_panel(
                self.trade_visualizer
            ),
            "Orders": self.panel_content_renderer.render_execution_panel(
                self.order_visualizer
            ),
            "Stop orders": self.panel_content_renderer.render_execution_panel(
                self.stop_order_visualizer
            ),
            "Session pair statistics": self.panel_content_renderer.render_stats_panel(
                self.session_pair_statistics_visualizer
            ),
            "Cumulative statistics": self.panel_content_renderer.render_stats_panel(
                self.cumulative_statistics_visualizer
            ),
            "News": self.panel_content_renderer.render_news_panel(
                self.news_visualizer
            )
        }

        return figures, panels


    def _register_callbacks(self):
        """Register Dash callbacks for periodic dashboard updates."""
        @self.app.callback(
            Output("price-chart-0", "figure"),
            Output("price-chart-1", "figure"),
            Output("last-week-chart", "figure"),
            Output("last-day-chart", "figure"),
            Output("session-pair-equity-curve", "figure"),
            Output("cumulative-equity-curve", "figure"),
            Output("session-pair-panel", "children"),
            Output("trade-panel", "children"),
            Output("order-panel", "children"),
            Output("stop-order-panel", "children"),
            Output("session-pair-stats-panel", "children"),
            Output("cumulative-stats-panel", "children"),
            Output("news-panel", "children"),
            Input("trigger-check", "n_intervals")
        )
        def update(_):
            figures, panels = self._build_dashboard_snapshot()
            
            return (*figures.values(), *panels.values())

    def add_price_chart_visualizer(self, visualizer: PriceChartVisualizer):
        """Add a price chart visualizer to the specified chart slot."""
        if visualizer.chart_slot not in (0, 1):
            raise ValueError("Price chart visualizer chart_slot must be 0 or 1")

        self.price_visualizers.append(visualizer)
        self.price_chart_count = max(self.price_chart_count, visualizer.chart_slot + 1)
        self.app.layout = self.layout.build(self.price_chart_count)
        return self

    def _get_price_visualizers(self, chart_slot: int):
        """Return price visualizers assigned to the specified chart slot."""
        return [
            visualizer
            for visualizer in self.price_visualizers
            if visualizer.chart_slot == chart_slot
        ]

    def add_context_chart_visualizer(self, visualizer: ContextChartVisualizer):
        """Add a context chart visualizer for its configured timeframe."""
        self.context_visualizers[visualizer.period].append(visualizer)
        return self
    
    def set_session_counter(self, session_counter: SessionCounter):
        """Set the session counter used by the dashboard."""
        self.session_counter = session_counter
        return self

    def set_execution_visualizers(self, trade_visualizer: TradeVisualizer, order_visualizer: OrderVisualizer, stop_order_visualizer: StopOrderVisualizer):
        """Set the visualizers used for trades, orders, and stop orders."""
        self.trade_visualizer = trade_visualizer
        self.order_visualizer = order_visualizer
        self.stop_order_visualizer = stop_order_visualizer
        return self

    def set_equity_curve_visualizers(self, session_pair_visualizer: EquityCurveVisualizer, cumulative_visualizer: EquityCurveVisualizer):
        """Set the visualizers used for session and cumulative equity curves."""
        self.session_pair_equity_visualizer = session_pair_visualizer
        self.cumulative_equity_visualizer = cumulative_visualizer
        return self
    
    def set_statistics_visualizers(self, session_pair_visualizer: StatisticsVisualizer, cumulative_visualizer: StatisticsVisualizer):
        """Set the visualizers used for session and cumulative statistics."""
        self.session_pair_statistics_visualizer = session_pair_visualizer
        self.cumulative_statistics_visualizer = cumulative_visualizer
        return self

    def set_news_visualizer(self, visualizer: NewsVisualizer):
        """Add a news visualizer to the dashboard."""
        self.news_visualizer = visualizer
        return self

    def run(self, debug=False):
        """Start the Dash application with the configured dashboard."""
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self.app.run(debug=debug, use_reloader=False)