from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from data_analysis.equity_curve.symbol_based import (
    SymbolBasedEquityCurveAnalyzer,
)
from data_analysis.statistics.symbol_based import (
    SymbolBasedStatisticsAnalyzer,
)
from global_services.data.provider import DataProvider
from trading.execution.data_analysis_handler import DataAnalysisHandler


def _closed_trade(realized_pnl):
    return SimpleNamespace(
        realized_pnl=Decimal(realized_pnl),
        fees_paid=Decimal("0"),
        open_time=0,
        close_time=1_000,
    )


@pytest.mark.parametrize("portfolio_balance", [Decimal("1600"), Decimal("700")])
@pytest.mark.parametrize("first_change", [Decimal("0"), Decimal("25")])
def test_symbol_curve_uses_run_balance_after_earlier_other_symbol_sessions(
    portfolio_balance, first_change,
):
    data_provider = DataProvider()
    analyzer = SymbolBasedEquityCurveAnalyzer("BTCUSDT", Decimal("1000"))
    analyzer.visualizer = Mock()
    handler = DataAnalysisHandler().add_equity_curve_analyzer(analyzer)

    assert analyzer.model.starting_balance == Decimal("1000")
    assert analyzer.model.content == {}
    assert analyzer.session_pair_boundaries == []

    data_provider.set_symbol("ETHUSDT")
    data_provider.set_time(1)
    handler.on_session_pair_start(Decimal("1000"))
    handler.update_on_price_change(Decimal("1000"))
    data_provider.set_time(2)
    handler.record_trade_event(portfolio_balance)
    handler.on_session_pair_end(portfolio_balance)

    assert analyzer.model.content == {}
    assert analyzer.session_pair_boundaries == []
    analyzer.visualizer.on_equity_curve_update.assert_not_called()

    data_provider.set_symbol("BTCUSDT")
    data_provider.set_time(10)
    handler.on_session_pair_start(portfolio_balance)
    assert analyzer.model.content == {}
    assert analyzer.session_pair_boundaries == []
    analyzer.visualizer.on_equity_curve_update.assert_not_called()

    handler.update_on_price_change(portfolio_balance + first_change)
    first_equity = Decimal("1000") + first_change
    assert list(analyzer.model.content.values()) == [first_equity]
    assert analyzer.session_pair_boundaries == [1]
    analyzer.visualizer.on_equity_curve_update.assert_called_once_with(
        1, first_equity
    )

    data_provider.set_time(11)
    handler.record_trade_event(portfolio_balance + Decimal("50"))
    handler.on_session_pair_end(portfolio_balance + Decimal("50"))
    assert list(analyzer.model.content.values()) == [
        first_equity,
        Decimal("1050"),
    ]
    assert analyzer.model.starting_balance == Decimal("1000")


def test_symbol_based_analyzers_exclude_intervening_symbols():
    data_provider = DataProvider()
    equity_analyzer = SymbolBasedEquityCurveAnalyzer(
        symbol="BTCUSDT",
        starting_balance=Decimal("1000"),
    )
    statistics_analyzer = SymbolBasedStatisticsAnalyzer(
        symbol="BTCUSDT",
        starting_balance=Decimal("1000"),
    )
    equity_analyzer.visualizer = Mock()
    statistics_analyzer.visualizer = Mock()
    handler = DataAnalysisHandler()
    handler.add_equity_curve_analyzer(equity_analyzer)
    handler.add_statistics_analyzer(statistics_analyzer)

    data_provider.set_symbol("BTCUSDT")
    data_provider.set_time(1)
    handler.on_session_pair_start(Decimal("1000"))
    handler.update_on_price_change(Decimal("1000"))
    data_provider.set_time(2)
    handler.record_trade_event(
        Decimal("1100"),
        closed_trade=_closed_trade("100"),
    )
    handler.on_session_pair_end(Decimal("1100"))

    data_provider.set_symbol("ETHUSDT")
    handler.on_session_pair_start(Decimal("1600"))
    handler.update_on_price_change(Decimal("1700"))
    handler.record_trade_event(
        Decimal("1700"),
        closed_trade=_closed_trade("600"),
    )
    handler.on_session_pair_end(Decimal("1700"))

    data_provider.set_symbol("BTCUSDT")
    data_provider.set_time(10)
    handler.on_session_pair_start(Decimal("2000"))
    handler.update_on_price_change(Decimal("2000"))
    assert equity_analyzer.model.content[3] == Decimal("1100")
    assert statistics_analyzer.model.equity == Decimal("1100")
    assert statistics_analyzer.model.roi == Decimal("0.1")

    data_provider.set_time(11)
    handler.record_trade_event(
        Decimal("2050"),
        closed_trade=_closed_trade("50"),
    )
    handler.on_session_pair_end(Decimal("2050"))

    assert list(equity_analyzer.model.content.values()) == [
        Decimal("1000"),
        Decimal("1100"),
        Decimal("1100"),
        Decimal("1150"),
    ]
    assert equity_analyzer.model.starting_balance == Decimal("1000")
    assert statistics_analyzer.model.starting_balance == Decimal("1000")
    assert statistics_analyzer.model.equity == Decimal("1150")
    assert statistics_analyzer.model.roi == Decimal("0.15")
    assert statistics_analyzer.model.pnl == Decimal("150")
    assert statistics_analyzer.model.total_trades == 2
