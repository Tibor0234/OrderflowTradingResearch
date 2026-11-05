from decimal import Decimal

from data_analysis.equity_curve.cumulative import CumulativeEquityCurveAnalyzer
from data_analysis.statistics.cumulative import CumulativeStatisticsAnalyzer
from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from trading.execution.data_analysis_handler import DataAnalysisHandler


def test_session_pair_start_uses_preinitialized_symbol_analyzers():
    data_provider = DataProvider()
    data_provider.set_symbol("BTCUSDT")
    handler = DataAnalysisHandler()
    unfiltered_curve = CumulativeEquityCurveAnalyzer()
    symbol_curve = CumulativeEquityCurveAnalyzer(symbol="BTCUSDT")
    unfiltered_statistics = CumulativeStatisticsAnalyzer()
    symbol_statistics = CumulativeStatisticsAnalyzer(symbol="BTCUSDT")
    handler.add_equity_curve_analyzer(unfiltered_curve)
    handler.add_equity_curve_analyzer(symbol_curve)
    handler.add_statistics_analyzer(unfiltered_statistics)
    handler.add_statistics_analyzer(symbol_statistics)

    handler.on_session_pair_start(Decimal("10000"))
    handler.on_session_pair_start(Decimal("10000"))

    symbol_curves = [
        curve
        for curve in handler.equity_curve_analyzers
        if isinstance(curve, CumulativeEquityCurveAnalyzer)
        and curve.model.symbol == "BTCUSDT"
    ]
    assert len(symbol_curves) == 1
    symbol_analyzers = [
        analyzer
        for analyzer in handler.statistics_analyzers
        if isinstance(analyzer, CumulativeStatisticsAnalyzer)
        and analyzer.model.symbol == "BTCUSDT"
    ]
    assert len(symbol_analyzers) == 1
    assert unfiltered_curve in handler.equity_curve_analyzers


def test_session_pair_start_does_not_create_analyzers_during_replay():
    data_provider = DataProvider()
    data_provider.set_symbol("BTCUSDT")
    handler = DataAnalysisHandler()

    handler.on_session_pair_start(Decimal("10000"))

    assert handler.equity_curve_analyzers == []
    assert handler.statistics_analyzers == []


def test_registered_analyzers_send_frontend_initialization():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    data_provider = DataProvider()
    data_analysis_handler = DataAnalysisHandler()
    equity_analyzer = CumulativeEquityCurveAnalyzer(symbol="BTCUSDT")
    statistics_analyzer = CumulativeStatisticsAnalyzer(symbol="BTCUSDT")
    data_analysis_handler.add_equity_curve_analyzer(equity_analyzer)
    data_analysis_handler.add_statistics_analyzer(statistics_analyzer)

    try:
        equity_analyzer.init_frontend()
        statistics_analyzer.init_frontend()
        data_provider.set_symbol("BTCUSDT")
        data_analysis_handler.on_session_pair_start(Decimal("10000"))
        data_analysis_handler.on_session_pair_start(Decimal("10000"))

        symbol_analyzers = [
            analyzer
            for analyzer in data_analysis_handler.statistics_analyzers
            if isinstance(analyzer, CumulativeStatisticsAnalyzer)
            and analyzer.model.symbol == "BTCUSDT"
        ]
        assert len(symbol_analyzers) == 1
        statistics_messages = [
            message
            for message in messages
            if message[1]["analysis_type"] == "statistics"
        ]
        assert statistics_messages[0] == (
            "analysis_init",
            {
                "analysis_type": "statistics",
                "target": "statistics/cumulative_BTCUSDT",
                "name": "BTCUSDT",
                "snapshot": {
                    "total_trades": 0,
                    "winrate": None,
                    "pnl": "0",
                    "roi": "0",
                    "max_drawdown": "0",
                    "average_trade_duration": None,
                },
            },
        )
        assert statistics_messages[1][0] == "analysis_update"
        assert len(statistics_messages) == 2
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)
