from dataclasses import dataclass
from decimal import Decimal

from data_analysis.statistics.model import Statistics


@dataclass(frozen=True)
class StyledStatisticValue:
    children: str
    style: dict[str, str]


class PlotlyStatisticsVisualizer:
    """Formats statistics as colored values for the report generator."""

    POSITIVE_COLOR = "#00c853"
    NEGATIVE_COLOR = "#ff4100"
    NEUTRAL_COLOR = "#ffffff"
    MUTED_COLOR = "#aaaaaa"
    PANEL_COLUMNS = (
        (
            "Trade outcomes",
            (
                "Total Trades",
                "Trades Won",
                "Trades Lost",
                "Win Rate",
                "Average Win",
                "Average Loss",
                "Average Trade Duration",
            ),
        ),
        (
            "Returns & risk",
            (
                "PnL",
                "ROI",
                "Profit Factor",
                "Expectancy",
                "Fees Paid",
                "Maximum Drawdown",
            ),
        ),
    )

    def __init__(self, model: Statistics):
        self.model = model

    def get_panel_content(self) -> tuple[list[str], list[StyledStatisticValue]]:
        model = self.model
        metrics = [
            ("Total Trades", f"{model.total_trades:,}", self.NEUTRAL_COLOR),
            ("Trades Won", f"{model.trades_won:,}", None),
            ("Trades Lost", f"{model.trades_lost:,}", None),
            (
                "Win Rate",
                self._percentage(model.winrate),
                self._threshold_color(model.winrate, 0.5),
            ),
            ("PnL", self._currency(model.pnl), self._sign_color(model.pnl)),
            (
                "Fees Paid",
                self._currency(model.fees_paid),
                None,
            ),
            ("ROI", self._percentage(model.roi), self._sign_color(model.roi)),
            (
                "Maximum Drawdown",
                self._percentage(model.max_drawdown),
                None,
            ),
            (
                "Profit Factor",
                self._number(model.profit_factor),
                self._threshold_color(model.profit_factor, 1),
            ),
            (
                "Expectancy",
                self._currency(model.expectency),
                self._sign_color(model.expectency),
            ),
            (
                "Average Win",
                self._currency(model.average_win),
                None,
            ),
            (
                "Average Loss",
                self._currency(model.average_loss),
                None,
            ),
            (
                "Average Trade Duration",
                self._duration(model.average_trade_duration),
                self.NEUTRAL_COLOR
                if model.average_trade_duration is not None
                else self.MUTED_COLOR,
            ),
        ]
        categories = [category for category, _, _ in metrics]
        values = [
            StyledStatisticValue(value, {"color": color} if color is not None else {})
            for _, value, color in metrics
        ]
        return categories, values

    def get_panel_columns(
        self,
    ) -> list[tuple[str, list[tuple[str, StyledStatisticValue]]]]:
        """Group statistics into trade outcomes and returns/risk columns."""
        categories, values = self.get_panel_content()
        values_by_category = dict(zip(categories, values))
        return [
            (
                column_title,
                [
                    (category, values_by_category[category])
                    for category in column_categories
                ],
            )
            for column_title, column_categories in self.PANEL_COLUMNS
        ]

    def _percentage(self, value: Decimal | float | None) -> str:
        if value is None:
            return "N/A"
        return f"{float(value) * 100:,.2f}%"

    def _currency(self, value: Decimal | float | None) -> str:
        if value is None:
            return "N/A"
        amount = float(value)
        sign = "-$" if amount < 0 else "$"
        return f"{sign}{abs(amount):,.2f}"

    def _number(self, value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:,.2f}"

    def _duration(self, value: float | None) -> str:
        if value is None:
            return "N/A"
        total_seconds = round(value)
        sign = "-" if total_seconds < 0 else ""
        hours, remainder = divmod(abs(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _sign_color(self, value: Decimal | float) -> str:
        if value >= 0:
            return self.POSITIVE_COLOR
        else:
            return self.NEGATIVE_COLOR

    def _threshold_color(self, value: float | None, threshold: float) -> str:
        if value is None:
            return self.MUTED_COLOR
        if value >= threshold:
            return self.POSITIVE_COLOR
        return self.NEGATIVE_COLOR
