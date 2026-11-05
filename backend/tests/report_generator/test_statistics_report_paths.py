from io import BytesIO
from decimal import Decimal

from pypdf import PdfReader

from data_analysis.equity_curve.model import EquityCurve
from data_analysis.statistics.model import Statistics
from data_analysis.utils import AnalysisType
from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from market_feed.utils import SessionCounter
from report_generator.plotly_visualizers.plotly_equity_curve_visualizer import (
    PlotlyEquityCurveVisualizer,
)
from report_generator.plotly_visualizers.plotly_report_visualizer import (
    PlotlyReportVisualizer,
)
from report_generator.plotly_visualizers.plotly_statistics_visualizer import (
    PlotlyStatisticsVisualizer,
)
from report_generator.statistics.cumulative import CumulativeReportStatistics
from report_generator.statistics.session_pair_based import (
    SessionPairBasedReportStatistics,
)


def _visualizers(analysis_type):
    equity_curve = EquityCurve(
        type=analysis_type,
        starting_balance=Decimal("1000"),
        content={1_700_000_000_000: Decimal("1000")},
    )
    statistics = Statistics(type=analysis_type)
    return (
        PlotlyEquityCurveVisualizer(equity_curve),
        PlotlyStatisticsVisualizer(statistics),
    )


def test_cumulative_report_writes_full_run_and_symbol_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(EventBus, "subscribe", lambda *_: None)
    monkeypatch.setattr(PlotlyReportVisualizer, "_get_symbol_logo", lambda *_: None)
    provider = DataProvider()
    monkeypatch.setattr(provider, "get_symbol", lambda: "BTCUSDT")

    full_run_visualizers = _visualizers(AnalysisType.CUMULATIVE)
    symbol_visualizers = _visualizers(AnalysisType.CUMULATIVE)
    report_generator = CumulativeReportStatistics(
        tmp_path,
        *full_run_visualizers,
        PlotlyReportVisualizer(),
        {"BTCUSDT": symbol_visualizers},
    )
    report_generator.replay_start_time = 1_700_000_000_000
    monkeypatch.setattr(report_generator, "_format_time_range", lambda _: "range")

    report_generator.generate_report()

    full_run_pdf = tmp_path / "cumulative-full_run.pdf"
    symbol_pdf = tmp_path / "cumulative-symbol-BTCUSDT.pdf"
    first_full_run_pdf = full_run_pdf.read_bytes()
    assert first_full_run_pdf.startswith(b"%PDF")
    assert symbol_pdf.read_bytes().startswith(b"%PDF")
    symbol_report_text = PdfReader(BytesIO(symbol_pdf.read_bytes())).pages[0].extract_text()
    assert "BTCUSDT" in symbol_report_text
    assert "Cumulative" not in symbol_report_text
    report_text = "\n".join(
        page.extract_text()
        for page in PdfReader(BytesIO(first_full_run_pdf)).pages
    )
    assert "Equity Curve" not in report_text
    assert "Statistics" not in report_text
    assert "Trade outcomes" in report_text
    assert "Returns & risk" in report_text

    full_run_visualizers[0].model.content[1_700_000_001_000] = Decimal("1200")
    report_generator.generate_report()

    updated_full_run_pdf = full_run_pdf.read_bytes()
    assert updated_full_run_pdf.startswith(b"%PDF")
    assert updated_full_run_pdf != first_full_run_pdf
    assert not (tmp_path / "cumulative").exists()


def test_session_pair_report_uses_session_pair_counter_filename(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(EventBus, "subscribe", lambda *_: None)
    monkeypatch.setattr(PlotlyReportVisualizer, "_get_symbol_logo", lambda *_: None)
    provider = DataProvider()
    monkeypatch.setattr(provider, "get_symbol", lambda: "BTCUSDT")

    report_generator = SessionPairBasedReportStatistics(
        tmp_path,
        *_visualizers(AnalysisType.SESSION_PAIR_BASED),
        PlotlyReportVisualizer(),
        SessionCounter(
            session=30,
            symbol="BTCUSDT",
            session_pair_count=7,
            selected_session_pairs=10,
        ),
    )
    monkeypatch.setattr(report_generator, "_format_time_range", lambda _: "range")

    report_generator.generate_report()

    report_path = tmp_path / "session_pair_based-7.pdf"
    assert report_path.read_bytes().startswith(b"%PDF")
    report_text = PdfReader(BytesIO(report_path.read_bytes())).pages[0].extract_text()
    assert "Session 30 - BTCUSDT" in report_text
    assert not (tmp_path / "session_pair_based").exists()
