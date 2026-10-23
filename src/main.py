import asyncio
import threading
from decimal import Decimal
from datetime import datetime
import os

import dotenv
import psycopg
import yaml

# ---- Market data & managers ----
from market_feed.feed import MarketFeed
from data_managers.open_interest.manager import OpenInterestManager
from data_managers.open_interest.subscriber import OpenInterestManagerSubscriber
from data_managers.order_book.manager import OrderBookManager
from data_managers.order_book.subscriber import OrderBookManagerSubscriber
from data_managers.trade.manager import TradeManager
from data_managers.trade.subscriber import TradeManagerSubscriber
from data_managers.ohlcv.manager import OHLCVManager
from data_managers.ohlcv.subscriber import OHLCVManagerSubscriber
from data_managers.news.manager import NewsManager
from data_managers.news.subscriber import NewsManagerSubscriber

# ---- Trading & session ----
from trading.execution.position_manager import PositionManager
from data_analysis.equity_curve.session_pair_based import SessionPairBasedEquityCurve
from data_analysis.equity_curve.cumulative import CumulativeEquityCurve
from data_analysis.statistics.session_pair_based import SessionPairBasedStatistics
from data_analysis.statistics.cumulative import CumulativeStatistics
from trading.execution.order_book import ExecutionOrderBook
from trading.execution.order_flow import ExecutionOrderFlow
from session_pairs.context import SessionPairContext
from strategies.core.framework import StrategyFramework
from report_generator.base import BaseReportGenerator
from report_generator.cumulative import CumulativeReportGenerator
from report_generator.session_pair_based import SessionPairBasedReportGenerator
from report_generator.trade_export import TradeExcelExporter
from ml.trade_export import MLTradeParquetExporter

# ---- Visualization ----
from dashboard.live_dashboard import LiveDashboard
from visualizers.market_entity.trade import TradeVisualizer
from visualizers.market_entity.order import OrderVisualizer
from visualizers.market_entity.stop_order import StopOrderVisualizer
from visualizers.data_analysis.equity_curve import EquityCurveVisualizer
from visualizers.data_analysis.statistics import StatisticsVisualizer
from visualizers.price_chart.base import PriceChartVisualizer
from visualizers.context_chart.base import ContextChartVisualizer
from visualizers.news_panel.news import NewsVisualizer

# ---- User config ----
from resource_config import ResourceConfig

# ------------------- MAIN -------------------
if __name__ == "__main__":
    with open("config.yaml", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    dotenv.load_dotenv()

    # ---- Essentials ----
    resource_config = ResourceConfig()
    strategy, resources, visualizers = resource_config.get_essentials()

    run_started_at = datetime.now()

    # ---- Dashboard ----
    dashboard = LiveDashboard('Trading dashboard')

    # ---- Equity & position management ----
    execution_order_book = ExecutionOrderBook()
    execution_order_flow = ExecutionOrderFlow()
    cumulative_equity_curve = CumulativeEquityCurve(
        refresh_rate=2_000,
        max_points=5_000
    )
    session_pair_based_equity_curve = SessionPairBasedEquityCurve(
        refresh_rate=250,
        max_points=2_000
    )
    cumulative_statistics = CumulativeStatistics()
    session_pair_statistics = SessionPairBasedStatistics()
    position_manager = PositionManager(
        starting_balance=Decimal(str(config["starting_balance"])),
        order_book=execution_order_book,
        order_flow=execution_order_flow,
        maker_fee_pct=Decimal(str(config["maker_fee_rate"])),
        taker_fee_pct=Decimal(str(config["taker_fee_rate"])),
    ) \
        .add_equity_curve(cumulative_equity_curve) \
        .add_equity_curve(session_pair_based_equity_curve) \
        .add_statistics(cumulative_statistics) \
        .add_statistics(session_pair_statistics)

    # ---- Session-pair context ----
    session_pair_context = SessionPairContext()

    # ---- Strategy setup ----
    strategy_framework = StrategyFramework(position_manager, session_pair_context, execution_order_book)
    strategy.init(strategy_framework)

    # ---- Managers ----
    open_interest_manager = OpenInterestManager()
    orderbook_manager = OrderBookManager().subscribe(execution_order_book)
    trade_manager = TradeManager().subscribe(execution_order_flow)
    news_manager = NewsManager()
    ohlcv_manager = OHLCVManager()

    # ---- DB Connection ----
    conn = psycopg.connect(os.getenv('POSTGRES_URL'))

    # ---- Market feed ----
    market_feed = MarketFeed(
        conn,
        open_interest_manager,
        orderbook_manager,
        trade_manager,
        news_manager,
        ohlcv_manager,
        session_numbers=config.get("session_ids", []),
        symbols=config.get("symbols", []),
    )

    # ---- Setup resources ----
    session_pair_context.set_resources(resources)

    for resource in resources.values():
        if isinstance(resource, TradeManagerSubscriber):
            trade_manager.subscribe(resource)
        elif isinstance(resource, OrderBookManagerSubscriber):
            orderbook_manager.subscribe(resource)
        elif isinstance(resource, OpenInterestManagerSubscriber):
            open_interest_manager.subscribe(resource)
        elif isinstance(resource, OHLCVManagerSubscriber):
            ohlcv_manager.subscribe(resource)
        elif isinstance(resource, NewsManagerSubscriber):
            news_manager.subscribe(resource)

    # ---- Setup visualizers ----
    # Trade & equity visualizers
    trade_visualizer = TradeVisualizer(position_manager.trades)
    order_visualizer = OrderVisualizer(position_manager.orders, position_manager.increase_orders)
    stop_order_visualizer = StopOrderVisualizer(position_manager.stop_orders)
    session_pair_equity_curve_visualizer = EquityCurveVisualizer(session_pair_based_equity_curve)
    cumulative_equity_curve_visualizer = EquityCurveVisualizer(cumulative_equity_curve)
    stats_config = config.get("statistics", {})
    dashboard_stats = [key for key, cfg in stats_config.items() if cfg.get("dashboard", True)]
    report_stats = [key for key, cfg in stats_config.items() if cfg.get("report", True)]

    def build_statistics_visualizers(stats_keys):
        return StatisticsVisualizer(session_pair_statistics, stats_keys), StatisticsVisualizer(cumulative_statistics, stats_keys)

    session_pair_statistics_dashboard_visualizer, cumulative_statistics_dashboard_visualizer = build_statistics_visualizers(dashboard_stats)
    session_pair_statistics_report_visualizer, cumulative_statistics_report_visualizer = build_statistics_visualizers(report_stats)

    dashboard \
        .set_execution_visualizers(trade_visualizer, order_visualizer, stop_order_visualizer) \
        .set_equity_curve_visualizers(session_pair_equity_curve_visualizer, cumulative_equity_curve_visualizer) \
        .set_statistics_visualizers(session_pair_statistics_dashboard_visualizer, cumulative_statistics_dashboard_visualizer) \
        .set_session_counter(market_feed.session_counter)

    # Price chart & context visualizers
    for visualizer in visualizers:
        if isinstance(visualizer, PriceChartVisualizer):
            dashboard.add_price_chart_visualizer(visualizer)
        elif isinstance(visualizer, ContextChartVisualizer):
            dashboard.add_context_chart_visualizer(visualizer)
        elif isinstance(visualizer, NewsVisualizer):
            dashboard.set_news_visualizer(visualizer)

    # Reports
    reports_config = config.get("reports", {})
    if reports_config.get("enabled", True):
        report_directory = BaseReportGenerator.create_report_directory(
            strategy.__class__.__name__,
            run_started_at,
        )
        session_pair_report_generator = SessionPairBasedReportGenerator(report_directory) \
            .set_visualizers(session_pair_equity_curve_visualizer, session_pair_statistics_report_visualizer) \
            .set_session_counter(market_feed.session_counter)
        cumulative_report_generator = CumulativeReportGenerator(report_directory) \
            .set_visualizers(cumulative_equity_curve_visualizer, cumulative_statistics_report_visualizer)
        trade_excel_exporter = TradeExcelExporter(
            report_directory,
            reports_config.get("export_shadow_trades", False),
        ).set_session_counter(market_feed.session_counter)

    # Machine-learning export
    ml_export_config = config.get("ml_export", {})
    if ml_export_config.get("enabled", False):
        ml_data_directory = ml_export_config.get("directory")
        if not ml_data_directory:
            raise ValueError("ml_export.directory must be set in config.yaml when ML export is enabled.")

        MLTradeParquetExporter(
            output_directory=ml_data_directory,
            schema_version=ml_export_config.get("schema_version", 1),
            strategy_name=strategy.__class__.__name__,
            run_started_at=run_started_at,
        ).set_session_counter(market_feed.session_counter)

    # ---- Start market feed in background thread ----
    threading.Thread(
        target=lambda: asyncio.run(market_feed.run()),
        daemon=True
    ).start()

    # ---- Run dashboard ----
    dashboard.run()