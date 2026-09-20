from dash import html
from market_feed.utils import SessionCounter
from visualizers.market_entity.trade import TradeVisualizer
from visualizers.data_analysis.statistics import StatisticsVisualizer
from visualizers.news_panel.news import NewsVisualizer

class PanelContentRenderer:
    """Builds dashboard panel content from application data."""

    def render_session_pair_panel(self, session_counter: SessionCounter):
        """Render the current session and session-pair progress."""
        return (
            f"Session: {session_counter.session_number} / {session_counter.total_sessions} | "
            f"{session_counter.symbol}  "
            f"Progress: {session_counter.session_pair} / "
            f"{session_counter.selected_session_pairs}"
        )

    def render_news_panel(self, news_visualizer: NewsVisualizer):
        """Render news data as an HTML table and headline list."""
        if news_visualizer is None:
            return html.Div()

        categories, values = news_visualizer.get_aggregated_features()
        headlines = news_visualizer.get_headlines()

        return html.Div([
            html.Table([
                html.Thead(
                    html.Tr([
                        html.Th(cat, style={"padding": "2px 6px", "color": "#aaa", "fontWeight": "bold", "textAlign": "center", "fontSize": "13px"})
                        for cat in categories
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(val, style={"padding": "2px 6px", "textAlign": "center", "fontSize": "13px"})
                        for val in values
                    ])
                ])
            ],
                style={"width": "100%", "backgroundColor": "#232323", "borderCollapse": "collapse", "margin": "0", "tableLayout": "auto"}
            ),

            html.Div([
                html.Div(headline, style={"padding": "2px 6px", "fontSize": "13px"})
                for headline in headlines
            ])
        ])

    def render_execution_panel(self, trade_visualizer: TradeVisualizer):
        """Render execution data as an HTML table."""
        categories, values = trade_visualizer.get_panel_content()

        return html.Table([
            html.Thead(
                html.Tr([
                    html.Th(cat, style={"padding": "2px 6px", "color": "#aaa", "fontWeight": "bold", "textAlign": "center", "fontSize": "13px"}) for cat in categories
                ])
            ),
            html.Tbody([
                html.Tr([
                    html.Td(val, style={"padding": "2px 6px", "textAlign": "center", "fontSize": "13px"}) for val in row
                ])
                for row in values
            ])
        ], 
        style={"width": "100%", "backgroundColor": "#232323", "borderCollapse": "collapse", "margin": "0", "tableLayout": "auto"}
        )

    def render_stats_panel(self, stats_visualizer: StatisticsVisualizer):
        """Render statistics data as an HTML table."""
        categories, values = stats_visualizer.get_panel_content()
        return html.Table([
            html.Tbody([
                html.Tr([
                    html.Td(cat, style={"padding": "7px 6px 7px 6px", "color": "#aaa", "fontWeight": "bold", "textAlign": "left", "fontSize": "13px"}),
                    html.Td(val, style={"padding": "7px 6px 7px 6px", "textAlign": "right", "fontSize": "13px"})
                ], style={"borderBottom": "2px solid #232323"}) for cat, val in zip(categories, values)
            ])
        ], style={"width": "100%", "backgroundColor": "#232323", "borderCollapse": "collapse", "margin": "0", "tableLayout": "auto"})
