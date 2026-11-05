from decimal import Decimal
from unittest.mock import Mock

import pytest

from data_analysis.statistics.cumulative import CumulativeStatisticsAnalyzer
from data_analysis.statistics.session_pair_based import SessionPairBasedStatisticsAnalyzer
from data_analysis.utils import AnalysisType
from global_services.data.provider import DataProvider
from trading.execution.data_analysis_handler import DataAnalysisHandler


def create_trade(realized_pnl, fees_paid="0"):
    trade = Mock()
    trade.realized_pnl = Decimal(realized_pnl)
    trade.fees_paid = Decimal(fees_paid)
    trade.open_time = 0
    trade.close_time = 2_000
    return trade


def test_cumulative_statistics_are_enabled_only_for_configured_symbol():
    data_provider = DataProvider()
    data_provider.set_symbol("BTCUSDT")
    analyzer = CumulativeStatisticsAnalyzer(symbol="BTCUSDT")
    analyzer.visualizer = Mock()

    assert analyzer.enabled is False
    analyzer.start_session_pair(Decimal("1000"))
    assert analyzer.enabled is True
    assert analyzer.model.type is AnalysisType.CUMULATIVE
    assert analyzer.model.starting_balance == Decimal("1000")

    analyzer.on_trade_event(Decimal("1100"))
    assert analyzer.model.equity == Decimal("1100")
    assert analyzer.model.roi == Decimal("0.1")
    assert analyzer.model.total_trades == 0

    analyzer.on_trade_event(
        Decimal("1120"),
        closed_trade=create_trade("20"),
    )
    assert analyzer.model.equity == Decimal("1120")
    assert analyzer.model.roi == Decimal("0.12")
    assert analyzer.model.total_trades == 1
    assert analyzer.model.pnl == Decimal("20")

    data_provider.set_symbol("ETHUSDT")
    analyzer.start_session_pair(Decimal("1100"))
    analyzer.on_trade_event(Decimal("900"))
    analyzer.on_trade_event(
        Decimal("910"),
        closed_trade=create_trade("10"),
    )
    assert analyzer.enabled is False
    assert analyzer.model.equity == Decimal("1120")
    assert analyzer.model.total_trades == 1
    assert analyzer.model.pnl == Decimal("20")

    data_provider.set_symbol("BTCUSDT")
    analyzer.start_session_pair(Decimal("1100"))
    assert analyzer.enabled is True
    assert analyzer.model.starting_balance == Decimal("1000")
    assert analyzer.model.total_trades == 1


def test_equity_observations_update_metrics_without_frontend_updates():
    data_provider = DataProvider()
    data_provider.set_symbol(None)
    analyzer = CumulativeStatisticsAnalyzer()
    analyzer.visualizer = Mock()
    analyzer.start_session_pair(Decimal("1000"))
    assert analyzer.model.winrate is None
    initial_update_count = analyzer.visualizer.on_statistics_update.call_count

    analyzer.observe_equity(Decimal("1100"))
    analyzer.observe_equity(Decimal("1050"))

    assert analyzer.model.equity == Decimal("1050")
    assert analyzer.model.roi == Decimal("0.05")
    assert analyzer.model.max_drawdown == Decimal("50") / Decimal("1100")
    assert analyzer.visualizer.on_statistics_update.call_count == initial_update_count


def test_trade_metrics_average_wins_losses_and_expectancy_correctly():
    analyzer = CumulativeStatisticsAnalyzer()
    analyzer.visualizer = Mock()
    analyzer.start_session_pair(Decimal("1000"))

    for pnl, fees_paid in (("100", "1"), ("50", "2"), ("-20", "3")):
        analyzer.on_trade_event(
            Decimal("1000"),
            closed_trade=create_trade(pnl, fees_paid),
        )
        if pnl != "-20":
            assert analyzer.model.profit_factor is None

    assert analyzer.model.total_trades == 3
    assert analyzer.model.trades_won == 2
    assert analyzer.model.trades_lost == 1
    assert analyzer.model.winrate == pytest.approx(2 / 3)
    assert analyzer.model.average_win == Decimal("75")
    assert analyzer.model.average_loss == Decimal("-20")
    assert analyzer.model.pnl == Decimal("130")
    assert analyzer.model.fees_paid == Decimal("6")
    assert analyzer.model.profit_factor == pytest.approx(7.5)
    assert analyzer.model.expectency == pytest.approx(130 / 3)


def test_average_trade_duration_includes_zero_duration_trades():
    analyzer = CumulativeStatisticsAnalyzer()
    analyzer.visualizer = Mock()
    analyzer.start_session_pair(Decimal("1000"))
    assert analyzer.model.average_trade_duration is None

    zero_duration_trade = create_trade("0")
    zero_duration_trade.close_time = zero_duration_trade.open_time
    analyzer.on_trade_event(Decimal("1000"), closed_trade=zero_duration_trade)
    analyzer.on_trade_event(
        Decimal("1000"),
        closed_trade=create_trade("0"),
    )

    assert analyzer.model.total_trades == 2
    assert analyzer.model.trades_lost == 0
    assert analyzer.model.winrate == 0
    assert analyzer.model.expectency == 0
    assert analyzer.model.average_trade_duration == 1


def test_session_pair_statistics_reset_only_for_configured_symbol():
    data_provider = DataProvider()
    data_provider.set_symbol("ETHUSDT")
    analyzer = SessionPairBasedStatisticsAnalyzer(symbol="BTCUSDT")
    analyzer.visualizer = Mock()

    analyzer.start_session_pair(Decimal("1000"))
    analyzer.on_trade_event(Decimal("1050"))
    assert analyzer.enabled is False
    assert analyzer.model.starting_balance is None

    data_provider.set_symbol("BTCUSDT")
    analyzer.start_session_pair(Decimal("1000"))
    analyzer.on_trade_event(Decimal("1100"))
    analyzer.on_trade_event(
        Decimal("1120"),
        closed_trade=create_trade("20"),
    )
    assert analyzer.enabled is True
    assert analyzer.model.type is AnalysisType.SESSION_PAIR_BASED
    assert analyzer.model.starting_balance == Decimal("1000")
    assert analyzer.model.equity == Decimal("1120")
    assert analyzer.model.total_trades == 1

    analyzer.start_session_pair(Decimal("2000"))
    assert analyzer.model.starting_balance == Decimal("2000")
    assert analyzer.model.equity == Decimal("2000")
    assert analyzer.model.total_trades == 0
    assert analyzer.model.pnl == Decimal("0")
    assert analyzer.model.winrate is None
    assert analyzer.model.fees_paid == Decimal("0")
    assert analyzer.model.profit_factor is None
    assert analyzer.model.average_trade_duration is None
    assert analyzer.visualizer.on_session_start.call_count == 2


def test_data_analysis_handler_manages_statistics_analyzers():
    data_provider = DataProvider()
    data_provider.set_symbol(None)
    handler = DataAnalysisHandler()
    analyzer = CumulativeStatisticsAnalyzer()
    analyzer.visualizer = Mock()
    handler.add_statistics_analyzer(analyzer)

    handler.on_session_pair_start(Decimal("1000"))
    handler.update_on_price_change(Decimal("1040"))
    assert analyzer.model.equity == Decimal("1040")
    assert analyzer.visualizer.on_statistics_update.call_count == 1

    handler.record_trade_event(Decimal("1050"))
    handler.record_trade_event(
        Decimal("1075"),
        closed_trade=create_trade("25"),
    )

    assert analyzer in handler.statistics_analyzers
    assert analyzer.model.equity == Decimal("1075")
    assert analyzer.model.total_trades == 1
    assert analyzer.model.pnl == Decimal("25")
    assert analyzer.visualizer.on_statistics_update.call_count == 3
