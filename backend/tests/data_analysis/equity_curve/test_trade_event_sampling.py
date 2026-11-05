from decimal import Decimal
from unittest.mock import Mock

import pytest

from data_analysis.equity_curve.cumulative import CumulativeEquityCurveAnalyzer
from data_analysis.equity_curve.session_pair_based import SessionPairBasedEquityCurveAnalyzer
from global_services.data.provider import DataProvider


@pytest.mark.parametrize(
    "curve_type",
    [CumulativeEquityCurveAnalyzer, SessionPairBasedEquityCurveAnalyzer],
)
def test_trade_events_record_segment_extrema_in_time_order(curve_type):
    data_provider = DataProvider()
    analyzer = curve_type()
    analyzer.start_session_pair()

    data_provider.set_time(1)
    analyzer.update(Decimal("100"))

    data_provider.set_time(2)
    analyzer.record_trade_event(Decimal("100"))

    data_provider.set_time(3)
    analyzer.update(Decimal("110"))
    data_provider.set_time(4)
    analyzer.update(Decimal("90"))
    assert len(analyzer.model.content) == 2

    data_provider.set_time(5)
    analyzer.record_trade_event(Decimal("105"))
    assert list(analyzer.model.content.values()) == [
        Decimal("100"),
        Decimal("100"),
        Decimal("110"),
        Decimal("90"),
        Decimal("105"),
    ]

    data_provider.set_time(6)
    analyzer.update(Decimal("120"))
    data_provider.set_time(7)
    analyzer.update(Decimal("80"))
    data_provider.set_time(8)
    analyzer.record_trade_event(Decimal("95"))

    data_provider.set_time(9)
    analyzer.update(Decimal("108"))
    data_provider.set_time(10)
    analyzer.update(Decimal("85"))
    data_provider.set_time(11)
    analyzer.record_trade_event(Decimal("100"))

    assert list(analyzer.model.content.values()) == [
        Decimal("100"),
        Decimal("100"),
        Decimal("110"),
        Decimal("90"),
        Decimal("105"),
        Decimal("120"),
        Decimal("80"),
        Decimal("95"),
        Decimal("108"),
        Decimal("85"),
        Decimal("100"),
    ]
    assert list(analyzer.model.content) == sorted(analyzer.model.content)


def test_cumulative_curve_keeps_points_and_pair_boundaries():
    data_provider = DataProvider()
    analyzer = CumulativeEquityCurveAnalyzer()

    data_provider.set_time(1)
    analyzer.update(Decimal("100"))
    first_pair_content = analyzer.model.content.copy()

    analyzer.start_session_pair()
    data_provider.set_time(10)
    analyzer.update(Decimal("105"))

    assert analyzer.model.content.keys() > first_pair_content.keys()
    assert len(analyzer.session_pair_boundaries) == 2


def test_cumulative_frontend_updates_use_appended_chart_times_between_pairs():
    data_provider = DataProvider()
    analyzer = CumulativeEquityCurveAnalyzer()
    analyzer.visualizer = Mock()

    data_provider.set_symbol("BTCUSDT")
    data_provider.set_time(1000)
    analyzer.start_session_pair()
    analyzer.update(Decimal("100"))

    data_provider.set_symbol("ETHUSDT")
    data_provider.set_time(500)
    analyzer.start_session_pair()
    analyzer.update(Decimal("110"))

    assert list(analyzer.model.content) == [1, 2]
    assert [
        call.args
        for call in analyzer.visualizer.on_equity_curve_update.call_args_list
    ] == [
        (1, Decimal("100")),
        (2, Decimal("110")),
    ]


@pytest.mark.parametrize(
    "curve_type",
    [CumulativeEquityCurveAnalyzer, SessionPairBasedEquityCurveAnalyzer],
)
def test_session_pair_end_records_pending_extrema_and_final_equity(curve_type):
    data_provider = DataProvider()
    analyzer = curve_type()
    analyzer.start_session_pair()

    data_provider.set_time(1)
    analyzer.update(Decimal("100"))
    data_provider.set_time(2)
    analyzer.update(Decimal("110"))
    data_provider.set_time(3)
    analyzer.update(Decimal("90"))
    data_provider.set_time(4)
    analyzer.record_session_pair_end(Decimal("105"))

    assert list(analyzer.model.content.values()) == [
        Decimal("100"),
        Decimal("110"),
        Decimal("90"),
        Decimal("105"),
    ]


def test_session_end_does_not_duplicate_a_trade_close_point():
    data_provider = DataProvider()
    analyzer = SessionPairBasedEquityCurveAnalyzer()
    analyzer.start_session_pair()

    data_provider.set_time(1)
    analyzer.record_trade_event(Decimal("100"))
    analyzer.record_session_pair_end(Decimal("100"))

    assert list(analyzer.model.content.values()) == [Decimal("100")]


def test_symbol_filtered_cumulative_curve_ignores_other_pairs(monkeypatch):
    data_provider = DataProvider()
    analyzer = CumulativeEquityCurveAnalyzer(symbol="BTCUSDT")
    get_symbol = Mock(side_effect=["ETHUSDT", "BTCUSDT"])
    monkeypatch.setattr(data_provider, "get_symbol", get_symbol)

    data_provider.set_symbol("ETHUSDT")
    data_provider.set_time(1)
    analyzer.start_session_pair()
    analyzer.update(Decimal("100"))
    analyzer.record_trade_event(Decimal("110"))
    analyzer.record_session_pair_end(Decimal("105"))
    assert analyzer.model.content == {}
    assert analyzer.session_pair_boundaries == []
    assert get_symbol.call_count == 1

    data_provider.set_symbol("BTCUSDT")
    data_provider.set_time(10)
    analyzer.update(Decimal("190"))
    assert analyzer.model.content == {}

    analyzer.start_session_pair()
    analyzer.update(Decimal("200"))
    data_provider.set_time(11)
    analyzer.record_session_pair_end(Decimal("200"))

    assert list(analyzer.model.content.values()) == [Decimal("200"), Decimal("200")]
    assert len(analyzer.session_pair_boundaries) == 1
    assert get_symbol.call_count == 2


def test_unfiltered_cumulative_curve_tracks_all_symbols():
    data_provider = DataProvider()
    analyzer = CumulativeEquityCurveAnalyzer()

    data_provider.set_symbol("BTCUSDT")
    data_provider.set_time(1)
    analyzer.start_session_pair()
    analyzer.update(Decimal("100"))

    data_provider.set_symbol("ETHUSDT")
    data_provider.set_time(2)
    analyzer.start_session_pair()
    analyzer.update(Decimal("110"))

    assert list(analyzer.model.content.values()) == [Decimal("100"), Decimal("110")]
    assert len(analyzer.session_pair_boundaries) == 2
