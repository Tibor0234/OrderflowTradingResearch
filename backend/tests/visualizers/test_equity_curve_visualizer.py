from decimal import Decimal
from unittest.mock import Mock

from data_analysis.equity_curve.cumulative import CumulativeEquityCurveAnalyzer
from data_analysis.equity_curve.model import EquityCurve
from data_analysis.equity_curve.session_pair_based import SessionPairBasedEquityCurveAnalyzer
from data_analysis.equity_curve.symbol_based import SymbolBasedEquityCurveAnalyzer
from data_analysis.utils import AnalysisType
from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.data_analysis.equity_curve_visualizer import EquityCurveVisualizer


def test_stored_equity_points_trigger_visualizer_updates():
    data_provider = DataProvider()
    data_provider.set_symbol("BTCUSDT")

    analyzer = CumulativeEquityCurveAnalyzer(symbol="BTCUSDT")
    analyzer.visualizer = Mock()
    analyzer.start_session_pair()
    assert analyzer.model.type is AnalysisType.CUMULATIVE

    data_provider.set_time(1)
    analyzer.update(Decimal("100"))
    assert analyzer.visualizer.on_equity_curve_update.call_count == 1

    data_provider.set_time(2)
    analyzer.update(Decimal("105"))
    assert analyzer.visualizer.on_equity_curve_update.call_count == 1

    data_provider.set_time(3)
    analyzer.record_trade_event(Decimal("100"))
    assert analyzer.visualizer.on_equity_curve_update.call_count == 3


def test_session_pair_start_resets_frontend_curve():
    analyzer = SessionPairBasedEquityCurveAnalyzer()
    assert analyzer.visualizer.model is analyzer.model
    assert analyzer.model.type is AnalysisType.SESSION_PAIR_BASED
    analyzer.visualizer = Mock()

    analyzer.start_session_pair()

    analyzer.visualizer.on_session_start.assert_called_once_with()


def test_equity_curve_init_and_updates_include_starting_balance():
    event_bus = EventBus()
    messages = []
    listener = lambda *args: messages.append(args)
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, listener)

    try:
        model = EquityCurve(
            type=AnalysisType.CUMULATIVE,
            starting_balance=Decimal("100"),
            content={1: Decimal("105")},
        )
        visualizer = EquityCurveVisualizer(model)

        visualizer.init_frontend()
        visualizer.on_equity_curve_update(2, Decimal("110"))
        visualizer.on_session_start()

        assert messages[0][1]["snapshot"]["starting_balance"] == "100"
        assert messages[1][1]["starting_balance"] == "100"
        assert messages[1][1]["equity"] == "110"
        assert messages[2][0] == "analysis_session_start"
        assert "starting_balance" not in messages[2][1]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(listener)


def test_symbol_curve_init_has_starting_balance_but_no_points():
    event_bus = EventBus()
    messages = []
    listener = lambda *args: messages.append(args)
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, listener)

    try:
        analyzer = SymbolBasedEquityCurveAnalyzer("BTCUSDT", Decimal("1000"))
        analyzer.init_frontend()

        assert messages[0][1]["snapshot"] == {
            "starting_balance": "1000",
            "points": [],
        }
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(listener)
