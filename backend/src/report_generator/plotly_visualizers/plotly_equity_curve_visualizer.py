from datetime import datetime, timedelta, timezone

import plotly.graph_objects as go

from data_analysis.equity_curve.model import EquityCurve
from data_analysis.utils import AnalysisType


class PlotlyEquityCurveVisualizer:
    """Builds a Plotly figure from the recorded equity-curve data."""

    GREEN = "#19c995"
    RED = "#f25c6c"
    MUTED = "#b8c2cc"
    WIDTH = 500
    HEIGHT = 184

    def __init__(self, model: EquityCurve):
        self.model = model

    def create_figure(self) -> go.Figure:
        """Create a frontend-styled equity curve and balance references."""
        timestamps = sorted(self.model.content)
        values = [float(self.model.content[timestamp]) for timestamp in timestamps]
        point_indices = list(range(len(values)))
        tick_indices = self._date_tick_indices(len(timestamps))

        scale_values = list(values)
        if values and self.model.starting_balance is not None:
            scale_values.append(float(self.model.starting_balance))

        if scale_values:
            minimum = min(scale_values)
            maximum = max(scale_values)
            padding = max((maximum - minimum) * 0.14, 20)
            y_range = [minimum - padding, maximum + padding]
            y_tick_values = [
                y_range[0] + (y_range[1] - y_range[0]) * index / 3
                for index in range(4)
            ]
            y_tick_text = [self._format_axis_value(value) for value in y_tick_values]
        else:
            y_range = [0, 1]
            y_tick_values = []
            y_tick_text = []

        x_range = (
            [-0.5, 0.5]
            if len(point_indices) < 2
            else [point_indices[0], point_indices[-1]]
        )
        figure = go.Figure(
            data=[
                go.Scatter(
                    x=point_indices,
                    y=values,
                    mode="lines",
                    line={"color": self.GREEN, "width": 2, "shape": "linear"},
                    fill="tozeroy",
                    fillcolor="rgba(25,201,149,0.12)",
                    cliponaxis=False,
                )
            ]
        )
        figure.update_layout(
            width=self.WIDTH,
            height=self.HEIGHT,
            autosize=False,
            margin={"l": 0, "r": 45, "t": 16, "b": 32},
            paper_bgcolor="#121212",
            plot_bgcolor="#121212",
            showlegend=False,
            font={"family": "Arial, sans-serif", "size": 11, "color": self.MUTED},
        )
        figure.update_xaxes(
            range=x_range,
            tickmode="array",
            tickvals=[tick_indices[index] for index in range(len(tick_indices))],
            ticktext=[
                self._format_date(timestamps[index]) for index in tick_indices
            ],
            tickfont={"size": 11, "color": self.MUTED},
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            fixedrange=True,
        )
        figure.update_yaxes(
            range=y_range,
            side="right",
            ticklabelposition="outside",
            tickmode="array",
            tickvals=y_tick_values,
            ticktext=y_tick_text,
            tickfont={"size": 11, "color": self.MUTED},
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            fixedrange=True,
        )

        if values:
            current_equity = values[-1]
            starting_label_shift = 8
            equity_label_shift = 8
            if self.model.starting_balance is not None:
                starting_balance = float(self.model.starting_balance)
                distance_pixels = (
                    abs(starting_balance - current_equity)
                    / (y_range[1] - y_range[0])
                    * 136
                )
                if distance_pixels < 14:
                    if starting_balance >= current_equity:
                        starting_label_shift = 22
                    else:
                        equity_label_shift = 22
                figure.add_shape(
                    type="line",
                    xref="paper",
                    x0=0,
                    x1=1,
                    yref="y",
                    y0=starting_balance,
                    y1=starting_balance,
                    line={"color": self.RED, "width": 1, "dash": "solid"},
                )
                figure.add_annotation(
                    xref="paper",
                    x=17 / 455,
                    xanchor="left",
                    yref="y",
                    y=starting_balance,
                    yshift=starting_label_shift,
                    text=f"Starting Balance {self._format_balance(starting_balance)}",
                    showarrow=False,
                    font={"size": 10, "color": self.RED},
                )

            figure.add_shape(
                type="line",
                xref="paper",
                x0=0,
                x1=1,
                yref="y",
                y0=current_equity,
                y1=current_equity,
                line={"color": self.MUTED, "width": 1, "dash": "dash"},
            )
            figure.add_annotation(
                xref="paper",
                x=17 / 455,
                xanchor="left",
                yref="y",
                y=current_equity,
                yshift=equity_label_shift,
                text=f"Equity {self._format_balance(current_equity)}",
                showarrow=False,
                font={"size": 10, "color": self.MUTED},
            )

        return figure

    def _chart_time(self, timestamp: int) -> datetime:
        if self.model.type is AnalysisType.CUMULATIVE:
            return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
                milliseconds=timestamp
            )
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

    def _date_tick_indices(self, point_count: int) -> list[int]:
        if point_count == 0:
            return []
        tick_count = min(point_count, 4)
        if tick_count == 1:
            return [0]
        return [
            round(index * (point_count - 1) / (tick_count - 1))
            for index in range(tick_count)
        ]

    def _format_date(self, timestamp: int) -> str:
        date = self._chart_time(timestamp)
        month = (
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        )[date.month - 1]
        return f"{date.day:02d} {month}"

    @staticmethod
    def _format_axis_value(value: float) -> str:
        sign = "-" if value < 0 else ""
        return f"{sign}${abs(value) / 1000:,.1f}k"

    @staticmethod
    def _format_balance(value: float) -> str:
        sign = "-" if value < 0 else ""
        return f"{sign}${abs(value):,.1f}"
