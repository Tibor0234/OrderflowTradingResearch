from decimal import Decimal

from data_analysis.statistics.model import Statistics
from data_analysis.utils import AnalysisType
from report_generator.plotly_visualizers.plotly_statistics_visualizer import (
    PlotlyStatisticsVisualizer,
)


def test_statistics_visualizer_formats_and_colors_statistics():
    model = Statistics(
        type=AnalysisType.CUMULATIVE,
        total_trades=12,
        trades_won=8,
        trades_lost=4,
        winrate=2 / 3,
        pnl=Decimal("1250.5"),
        fees_paid=Decimal("25"),
        roi=Decimal("0.125"),
        max_drawdown=Decimal("0.05"),
        profit_factor=1.5,
        expectency=Decimal("104.2"),
        average_win=Decimal("200"),
        average_loss=Decimal("-80"),
        average_trade_duration=3661.8,
    )

    categories, values = PlotlyStatisticsVisualizer(model).get_panel_content()
    value_by_category = dict(zip(categories, values))

    assert value_by_category["Total Trades"].children == "12"
    assert value_by_category["Win Rate"].children == "66.67%"
    assert value_by_category["PnL"].children == "$1,250.50"
    assert value_by_category["Average Loss"].children == "-$80.00"
    assert value_by_category["Average Trade Duration"].children == "01:01:02"
    assert value_by_category["PnL"].style["color"] == "#00c853"
    for category in (
        "Trades Won",
        "Trades Lost",
        "Fees Paid",
        "Maximum Drawdown",
        "Average Win",
        "Average Loss",
    ):
        assert "color" not in value_by_category[category].style


def test_statistics_visualizer_marks_unavailable_values():
    model = Statistics(type=AnalysisType.SESSION_PAIR_BASED)

    categories, values = PlotlyStatisticsVisualizer(model).get_panel_content()
    value_by_category = dict(zip(categories, values))

    assert value_by_category["Win Rate"].children == "N/A"
    assert value_by_category["Win Rate"].style["color"] == "#aaaaaa"
    assert value_by_category["Average Trade Duration"].children == "N/A"


def test_statistics_visualizer_groups_metrics_into_two_columns():
    visualizer = PlotlyStatisticsVisualizer(
        Statistics(type=AnalysisType.CUMULATIVE)
    )

    columns = visualizer.get_panel_columns()

    assert [title for title, _ in columns] == ["Trade outcomes", "Returns & risk"]
    assert [category for category, _ in columns[0][1]] == [
        "Total Trades",
        "Trades Won",
        "Trades Lost",
        "Win Rate",
        "Average Win",
        "Average Loss",
        "Average Trade Duration",
    ]
    assert [category for category, _ in columns[1][1]] == [
        "PnL",
        "ROI",
        "Profit Factor",
        "Expectancy",
        "Fees Paid",
        "Maximum Drawdown",
    ]
