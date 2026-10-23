from dash import html, dcc
import plotly.graph_objects as go

class DashboardLayout:
    """Builds the Dash layout for the trading dashboard."""

    def build(self, price_chart_count=1):
        """Build the complete dashboard layout."""
        return html.Div(
            style={
                "height": "100vh",
                "display": "flex",
                "flexDirection": "column",
                "backgroundColor": "#121212",
                "color": "white"
            },
            children=[
                self._main_row(price_chart_count),
                self._interval()
            ]
        )

    def _main_row(self, price_chart_count):
        """Build the main dashboard row containing the sidebars and charts."""
        return html.Div(
            style={
                "flex": "1",
                "display": "flex",
                "flexDirection": "row"
            },
            children=[
                self._left_sidebar(),
                self._price_chart(price_chart_count),
                self._right_panel()
            ]
        )

    def _left_sidebar(self):
        """Build the left sidebar with context charts and news."""
        return html.Div(
            style={
                "flex": "1.5",
                "display": "flex",
                "flexDirection": "column",
                "borderRight": "1px solid #333",
                "backgroundColor": "#1e1e1e"
            },
            children=[

                html.Div(
                    id="session-pair-panel",
                    style={
                        "flex": "0.3",
                        "padding": "15px 10px",
                        "borderTop": "1px solid #333",
                        "backgroundColor": "#232323",
                        "textAlign": "center",
                        "color": "#ddd",
                        "fontWeight": "bold",
                        "fontSize": "24px",
                        "letterSpacing": "1px",
                        "textTransform": "uppercase"
                    },
                    children="Session Pair"
                ),

                html.Div(
                    "Last Day Context",
                    style={"textAlign": "center", "padding": "4px", "fontWeight": "bold"}
                ),

                dcc.Graph(
                    id="last-day-chart",
                    style={"flex": "3"},
                    figure=go.Figure(),
                    config={"displayModeBar": False},
                ),

                html.Div(
                    "Last Week Context",
                    style={"textAlign": "center", "padding": "4px", "fontWeight": "bold"}
                ),

                dcc.Graph(
                    id="last-week-chart",
                    style={"flex": "3"},
                    figure=go.Figure(),
                    config={"displayModeBar": False},
                ),

                html.Div(
                    id="news-panel",
                    style={
                        "flex": "2",
                        "padding": "10px",
                        "borderTop": "1px solid #333",
                        "backgroundColor": "#232323"
                    },
                    children="News Panel"
                )
            ]
        )

    def _price_chart(self, price_chart_count):
        """Build the price chart section."""
        return html.Div(
            style={
                "flex": "4",
                "display": "flex",
                "flexDirection": "column",
                "backgroundColor": "#181818",
            },
            children=[
                dcc.Graph(
                    id="price-chart-0",
                    style={"flex": "1"},
                    figure=go.Figure(),
                    config={"displayModeBar": False},
                ),
                dcc.Graph(
                    id="price-chart-1",
                    style={"flex": "1"} if price_chart_count > 1 else {"display": "none"},
                    figure=go.Figure(),
                    config={"displayModeBar": False},
                ),
            ],
        )

    def _right_panel(self):
        """Build the right panel with statistics and order information."""
        return html.Div(
            style={
                "flex": "2",
                "display": "flex",
                "flexDirection": "column"
            },
            children=[
                html.Div(
                    style={
                        "flex": "1.25",
                        "display": "flex",
                        "flexDirection": "row"
                    },
                    children=[
                        self._session_column(),
                        self._cumulative_column()
                    ]
                ),

                html.Div(
                    style={
                        "flex": "1",
                        "display": "flex",
                        "flexDirection": "column",
                        "borderTop": "1px solid #333",
                        "backgroundColor": "#232323",
                        "padding": "5px"
                    },
                    children=[
                        html.Div(
                            id="trade-panel",
                            style={
                                "flex": "1",
                                "padding": "10px",
                                "borderBottom": "1px solid #333",
                                "backgroundColor": "#2a2a2a"
                            },
                        ),
                        html.Div(
                            id="order-panel",
                            style={
                                "flex": "1",
                                "padding": "10px",
                                "borderBottom": "1px solid #333",
                                "backgroundColor": "#2a2a2a"
                            },
                        ),
                        html.Div(
                            id="stop-order-panel",
                            style={
                                "flex": "1",
                                "padding": "10px",
                                "backgroundColor": "#2a2a2a"
                            },
                        )
                    ]
                )
            ]
        )

    def _session_column(self):
        """Build the session statistics column."""
        return html.Div(
            style={
                "flex": "1",
                "display": "flex",
                "flexDirection": "column",
                "borderRight": "1px solid #333",
                "backgroundColor": "#1e1e1e"
            },
            children=[

                html.Div(
                    "Session Pair Stats",
                    style={"textAlign": "center", "padding": "4px", "fontWeight": "bold"}
                ),

                dcc.Graph(
                    id="session-pair-equity-curve",
                    style={"flex": "1"},
                    figure=go.Figure(),
                    config={"displayModeBar": False},
                ),

                html.Div(
                    id="session-pair-stats-panel",
                    style={
                        "flex": "1",
                        "padding": "10px",
                        "borderTop": "1px solid #333",
                        "overflowY": "auto",
                        "backgroundColor": "#232323"
                    },
                    children=[
                        html.Div(id="session-pair-stats-content")
                    ]
                )
            ]
        )

    def _cumulative_column(self):
        """Build the cumulative statistics column."""
        return html.Div(
            style={
                "flex": "1",
                "display": "flex",
                "flexDirection": "column",
                "backgroundColor": "#1e1e1e"
            },
            children=[

                html.Div(
                    "Cumulative Stats",
                    style={"textAlign": "center", "padding": "4px", "fontWeight": "bold"}
                ),

                dcc.Graph(
                    id="cumulative-equity-curve",
                    style={"flex": "1"},
                    figure=go.Figure(),
                    config={"displayModeBar": False},
                ),

                html.Div(
                    id="cumulative-stats-panel",
                    style={
                        "flex": "1",
                        "padding": "10px",
                        "borderTop": "1px solid #333",
                        "overflowY": "auto",
                        "backgroundColor": "#232323"
                    },
                    children=[
                        html.Div(id="cumulative-stats-content")
                    ]
                )
            ]
        )

    def _interval(self):
        """Create the interval component used to trigger dashboard updates."""
        return dcc.Interval(
            id="trigger-check",
            interval=1000,
            n_intervals=0
        )