from decimal import Decimal
from unittest.mock import Mock

from data_analysis.equity_curve.session_pair_based import SessionPairBasedEquityCurveAnalyzer
from global_services.data.provider import DataProvider
from trading.execution.data_analysis_handler import DataAnalysisHandler
from trading.execution.position_manager import PositionManager
from trading.market_entities.order import MarketOrder
from trading.market_entities.trade import Trade
from trading.market_entities.utils import Side


class TestPositionManager:

    def setup_method(self):
        self.order_book = Mock()
        self.order_flow = Mock()

        self.position_manager = PositionManager(
            starting_balance=10000,
            order_book=self.order_book,
            order_flow=self.order_flow,
            data_analysis_handler=DataAnalysisHandler(),
        )

    def test_initial_state(self):
        pm = self.position_manager

        assert pm.starting_balance == Decimal("10000")
        assert pm.realized_balance == Decimal("10000")

        assert pm.trades == []
        assert pm.orders == []
        assert pm.increase_orders == []
        assert pm.stop_orders == []

    def test_place_order_delegates_to_order_execution(self):
        order = MarketOrder(
            side=Side.BUY,
            margin=Decimal("1000"),
            leverage=10,
        )

        self.position_manager.order_execution.place_order = Mock()

        self.position_manager.place_order(order)

        self.position_manager.order_execution.place_order.assert_called_once_with(
            order
        )

    def test_cancel_order_delegates_to_order_execution(self):
        order = MarketOrder(
            side=Side.BUY,
            margin=Decimal("1000"),
            leverage=10,
        )

        self.position_manager.order_execution.cancel_order = Mock()

        self.position_manager.cancel_order(order)

        self.position_manager.order_execution.cancel_order.assert_called_once_with(
            order
        )

    def test_on_order_triggered_delegates_to_order_execution(self):
        order = MarketOrder(
            side=Side.BUY,
            margin=Decimal("1000"),
            leverage=10,
        )

        self.position_manager.order_execution.on_order_triggered = Mock()

        self.position_manager.on_order_triggered(order)

        self.position_manager.order_execution.on_order_triggered.assert_called_once_with(
            order
        )

    def test_on_price_update_refreshes_trade_pnl(self):
        self.position_manager.position_visualizer.update_trade_pnls = Mock()

        self.position_manager.on_price_update()

        self.position_manager.position_visualizer.update_trade_pnls.assert_called_once()

    def test_clear_state(self):
        pm = self.position_manager

        pm.orders.append(Mock())
        pm.increase_orders.append(Mock())
        pm.stop_orders.append(Mock())
        pm.trades.append(Mock())

        pm.clear_state()

        assert pm.orders == []
        assert pm.increase_orders == []
        assert pm.stop_orders == []
        assert pm.trades == []

    def test_floating_balance_ignores_shadow_trades(self):
        pm = self.position_manager

        normal_trade = Mock()
        normal_trade.is_shadow = False
        normal_trade.floating_pnl = Decimal("250")

        shadow_trade = Mock()
        shadow_trade.is_shadow = True
        shadow_trade.floating_pnl = Decimal("1000")

        pm.trades.extend([normal_trade, shadow_trade])

        assert pm.floating_balance == Decimal("250")

    def test_total_balance(self):
        pm = self.position_manager

        trade = Mock()
        trade.is_shadow = False
        trade.margin = Decimal("1000")
        trade.floating_pnl = Decimal("250")

        pm.trades.append(trade)
        pm.realized_balance = Decimal("9000")

        assert pm.total_balance == Decimal("10250")

    def test_session_pair_end_records_equity_curve_endpoint(self):
        equity_curve_analyzer = SessionPairBasedEquityCurveAnalyzer()
        self.position_manager.data_analysis_handler.add_equity_curve_analyzer(
            equity_curve_analyzer
        )
        DataProvider().set_time(1)

        self.position_manager.on_session_pair_end()

        assert equity_curve_analyzer.model.content == {1: Decimal("10000")}