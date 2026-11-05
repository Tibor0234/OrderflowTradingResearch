from decimal import Decimal
from urllib.request import Request

from data_analysis.equity_curve.model import EquityCurve
from data_analysis.statistics.model import Statistics
from data_analysis.utils import AnalysisType
from report_generator.plotly_visualizers.plotly_equity_curve_visualizer import (
    PlotlyEquityCurveVisualizer,
)
from report_generator.plotly_visualizers.plotly_report_visualizer import (
    PlotlyReportVisualizer,
)
from report_generator.plotly_visualizers.plotly_statistics_visualizer import (
    PlotlyStatisticsVisualizer,
)


def test_plotly_equity_curve_visualizer_builds_trace_and_starting_balance():
    model = EquityCurve(
        type=AnalysisType.SESSION_PAIR_BASED,
        starting_balance=Decimal("1000"),
        content={
            1_700_000_000_000: Decimal("1000"),
            1_700_000_001_000: Decimal("1100"),
        },
    )

    figure = PlotlyEquityCurveVisualizer(model).create_figure()

    assert list(figure.data[0].x) == [0, 1]
    assert list(figure.data[0].y) == [1000.0, 1100.0]
    assert figure.data[0].line.color == "#19c995"
    assert figure.data[0].fill == "tozeroy"
    assert figure.data[0].fillcolor == "rgba(25,201,149,0.12)"
    assert figure.layout.width == 500
    assert figure.layout.height == 184
    assert figure.layout.margin.l == 0
    assert figure.layout.margin.r == 45
    assert list(figure.layout.xaxis.ticktext) == ["14 Nov", "14 Nov"]
    assert figure.layout.xaxis.tickfont.size == 11
    assert figure.layout.xaxis.showgrid is False
    assert figure.layout.yaxis.showgrid is False
    assert list(figure.layout.yaxis.range) == [980.0, 1120.0]
    assert list(figure.layout.yaxis.ticktext) == ["$1.0k", "$1.0k", "$1.1k", "$1.1k"]
    assert figure.layout.shapes[0].y0 == 1000.0
    assert figure.layout.shapes[0].line.color == "#f25c6c"
    assert figure.layout.shapes[0].line.dash == "solid"
    assert figure.layout.shapes[1].y0 == 1100.0
    assert figure.layout.shapes[1].line.color == "#b8c2cc"
    assert figure.layout.yaxis.side == "right"
    assert figure.layout.yaxis.ticklabelposition == "outside"
    assert figure.layout.shapes[0].line.width == figure.layout.shapes[1].line.width
    assert figure.layout.shapes[1].line.dash == "dash"
    assert [annotation.text for annotation in figure.layout.annotations] == [
        "Starting Balance $1,000.0",
        "Equity $1,100.0",
    ]
    assert figure.layout.annotations[0].x == figure.layout.annotations[1].x
    assert figure.layout.annotations[0].xanchor == "left"
    assert figure.layout.annotations[1].xanchor == "left"
    assert figure.layout.annotations[0].yshift > 0
    assert figure.layout.annotations[1].yshift > 0


def test_cumulative_equity_curve_uses_elapsed_time():
    model = EquityCurve(
        type=AnalysisType.CUMULATIVE,
        starting_balance=Decimal("1000"),
        content={1: Decimal("1000"), 3_601_001: Decimal("900")},
    )

    figure = PlotlyEquityCurveVisualizer(model).create_figure()

    assert list(figure.data[0].x) == [0, 1]
    assert list(figure.data[0].y) == [1000.0, 900.0]
    assert figure.data[0].line.color == "#19c995"
    assert figure.layout.shapes[1].y0 == 900.0


def test_empty_equity_curve_has_no_reference_markers():
    model = EquityCurve(
        type=AnalysisType.SESSION_PAIR_BASED,
        starting_balance=Decimal("1000"),
    )

    figure = PlotlyEquityCurveVisualizer(model).create_figure()

    assert list(figure.data[0].x) == []
    assert list(figure.data[0].y) == []
    assert len(figure.layout.shapes) == 0
    assert len(figure.layout.annotations) == 0
    assert list(figure.layout.yaxis.tickvals) == []


def test_balance_labels_use_en_us_currency_format():
    assert PlotlyEquityCurveVisualizer._format_balance(-1234.56) == "-$1,234.6"


def test_report_symbol_logo_url_normalizes_and_removes_quote_asset():
    assert (
        PlotlyReportVisualizer._symbol_logo_url(" eth/usdt ")
        == "https://assets.coincap.io/assets/icons/eth@2x.png"
    )
    assert PlotlyReportVisualizer._symbol_logo_url("None") is None
    assert PlotlyReportVisualizer._symbol_logo_url("—") is None
    assert PlotlyReportVisualizer._symbol_logo_url("USDT") is None


def test_report_symbol_logo_is_downloaded_and_cached(monkeypatch):
    class LogoResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _):
            return b"logo"

    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return LogoResponse()

    monkeypatch.setattr(
        "report_generator.plotly_visualizers.plotly_report_visualizer.urlopen",
        fake_urlopen,
    )
    visualizer = PlotlyReportVisualizer()

    assert visualizer._get_symbol_logo("BTCUSDT") == b"logo"
    assert visualizer._get_symbol_logo("BTCUSDT") == b"logo"
    assert len(requests) == 1
    request, timeout = requests[0]
    assert isinstance(request, Request)
    assert request.full_url == "https://assets.coincap.io/assets/icons/btc@2x.png"
    assert timeout == visualizer.SYMBOL_LOGO_TIMEOUT_SECONDS


def test_statistics_pdf_uses_plotly_equity_curve(tmp_path):
    model = EquityCurve(
        type=AnalysisType.SESSION_PAIR_BASED,
        starting_balance=Decimal("1000"),
        content={
            1_700_000_000_000: Decimal("1000"),
            1_700_000_001_000: Decimal("1100"),
        },
    )

    report_path = tmp_path / "summary.pdf"
    PlotlyReportVisualizer().render_pdf(
        report_path,
        "Summary",
        "2023-11-14 22:13:20 - 2023-11-14 22:13:21",
        PlotlyEquityCurveVisualizer(model),
        PlotlyStatisticsVisualizer(Statistics(type=AnalysisType.SESSION_PAIR_BASED)),
    )

    assert report_path.read_bytes().startswith(b"%PDF")
