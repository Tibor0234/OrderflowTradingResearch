import asyncio
from decimal import Decimal
from datetime import datetime
import os
import shutil
from pathlib import Path

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
from analyzers.timeframe.analyzer import TimeframeAnalyzer
from data_managers.ohlcv.manager import OHLCVManager
from data_managers.ohlcv.subscriber import OHLCVManagerSubscriber
from data_managers.news.manager import NewsManager
from data_managers.news.subscriber import NewsManagerSubscriber

# ---- Trading & session ----
from trading.execution.position_manager import PositionManager
from data_analysis.equity_curve.session_pair_based import SessionPairBasedEquityCurveAnalyzer
from data_analysis.equity_curve.cumulative import CumulativeEquityCurveAnalyzer
from data_analysis.equity_curve.symbol_based import SymbolBasedEquityCurveAnalyzer
from data_analysis.statistics.session_pair_based import SessionPairBasedStatisticsAnalyzer
from data_analysis.statistics.cumulative import CumulativeStatisticsAnalyzer
from data_analysis.statistics.symbol_based import SymbolBasedStatisticsAnalyzer
from trading.execution.order_book import ExecutionOrderBook
from trading.execution.order_flow import ExecutionOrderFlow
from trading.execution.data_analysis_handler import DataAnalysisHandler
from session_pairs.context import SessionPairContext
from visualizers.run_lifecycle.run_lifecycle_visualizer import RunLifecycleVisualizer
from strategies.core.framework import StrategyFramework
from report_generator.statistics.cumulative import CumulativeReportStatistics
from report_generator.statistics.session_pair_based import SessionPairBasedReportStatistics
from report_generator.report_zip_exporter import ReportZipExporter
from report_generator.plotly_visualizers.plotly_equity_curve_visualizer import PlotlyEquityCurveVisualizer
from report_generator.plotly_visualizers.plotly_report_visualizer import PlotlyReportVisualizer
from report_generator.plotly_visualizers.plotly_statistics_visualizer import PlotlyStatisticsVisualizer
from report_generator.trade.excel_export import TradeExcelExporter
from ml.trade_export import MLTradeParquetExporter
from communication import (
    CommunicationServer,
    ReplayApi,
    ReportExportApi,
    WebSocketMessageForwarder,
    WebSocketService,
)
from market_feed.controller import MarketFeedController

# ---- User config ----
from resource_config import ResourceConfig

# ------------------- MAIN -------------------
if __name__ == "__main__":
    with open("config.yaml", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    dotenv.load_dotenv()

    run_started_at = datetime.now()
    report_directory = Path("reports")
    report_directory.mkdir(parents=True, exist_ok=True)
    for report_item in report_directory.iterdir():
        if report_item.is_dir() and not report_item.is_symlink():
            shutil.rmtree(report_item)
        else:
            report_item.unlink()

    # ---- Essentials ----
    resource_config = ResourceConfig()
    strategy, resources = resource_config.get_essentials()

    # ---- Equity & position management ----
    execution_order_book = ExecutionOrderBook()
    execution_order_flow = ExecutionOrderFlow()
    cumulative_equity_curve_analyzer = CumulativeEquityCurveAnalyzer()
    session_pair_based_equity_curve_analyzer = SessionPairBasedEquityCurveAnalyzer()
    cumulative_statistics_analyzer = CumulativeStatisticsAnalyzer()
    session_pair_statistics_analyzer = SessionPairBasedStatisticsAnalyzer()
    data_analysis_handler = DataAnalysisHandler()
    position_manager = PositionManager(
        starting_balance=Decimal(str(config["starting_balance"])),
        order_book=execution_order_book,
        order_flow=execution_order_flow,
        data_analysis_handler=data_analysis_handler,
        maker_fee_pct=Decimal(str(config["maker_fee_rate"])),
        taker_fee_pct=Decimal(str(config["taker_fee_rate"])),
    )
    position_manager.data_analysis_handler \
        .add_equity_curve_analyzer(cumulative_equity_curve_analyzer) \
        .add_equity_curve_analyzer(session_pair_based_equity_curve_analyzer) \
        .add_statistics_analyzer(cumulative_statistics_analyzer) \
        .add_statistics_analyzer(session_pair_statistics_analyzer)

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

    run_lifecycle_visualizer = RunLifecycleVisualizer(
        strategy.__class__.__name__,
        market_feed.get_session_counter(),
    )

    # ---- Reports ----
    report_zip_exporter = ReportZipExporter(
            report_directory,
            strategy.__class__.__name__,
        )

    symbol_visualizers = {}
    for symbol in market_feed.get_session_counter().selected_symbols:
        equity_curve_analyzer = SymbolBasedEquityCurveAnalyzer(
            symbol=symbol,
            starting_balance=position_manager.starting_balance,
        )
        statistics_analyzer = SymbolBasedStatisticsAnalyzer(
            symbol=symbol,
            starting_balance=position_manager.starting_balance,
        )
        data_analysis_handler \
            .add_equity_curve_analyzer(equity_curve_analyzer) \
            .add_statistics_analyzer(statistics_analyzer)
        symbol_visualizers[symbol] = (
            PlotlyEquityCurveVisualizer(equity_curve_analyzer.model),
            PlotlyStatisticsVisualizer(statistics_analyzer.model),
        )

    plotly_report_visualizer = PlotlyReportVisualizer()
    cumulative_report_statistics = CumulativeReportStatistics(
        report_directory,
        PlotlyEquityCurveVisualizer(cumulative_equity_curve_analyzer.model),
        PlotlyStatisticsVisualizer(cumulative_statistics_analyzer.model),
        plotly_report_visualizer,
        symbol_visualizers,
    )
    session_pair_report_statistics = SessionPairBasedReportStatistics(
        report_directory,
        PlotlyEquityCurveVisualizer(session_pair_based_equity_curve_analyzer.model),
        PlotlyStatisticsVisualizer(session_pair_statistics_analyzer.model),
        plotly_report_visualizer,
        market_feed.get_session_counter(),
    )

    # ---- Setup resources ----
    session_pair_context.set_resources(resources)

    for resource in resources.values():
        if isinstance(resource, TimeframeAnalyzer):
            trade_manager.subscribe_timeframe(resource)
        elif isinstance(resource, TradeManagerSubscriber):
            trade_manager.subscribe(resource)
        elif isinstance(resource, OrderBookManagerSubscriber):
            orderbook_manager.subscribe(resource)
        elif isinstance(resource, OpenInterestManagerSubscriber):
            open_interest_manager.subscribe(resource)
        elif isinstance(resource, OHLCVManagerSubscriber):
            ohlcv_manager.subscribe(resource)
        elif isinstance(resource, NewsManagerSubscriber):
            news_manager.subscribe(resource)

    # ---- Trade export ----
    trade_excel_exporter = TradeExcelExporter(
        report_directory,
        market_feed.get_session_counter(),
        export_shadow_trades=True,
    )

    """
    # Machine-learning export
    ml_export_config = config.get("ml_export", {})
    if ml_export_config.get("enabled", False):
        ml_data_directory = ml_export_config.get("directory")
        if not ml_data_directory:
            raise ValueError("ml_export.directory must be set in config.yaml when ML export is enabled.")

        MLTradeParquetExporter(
            output_directory=ml_data_directory,
            schema_version=ml_export_config.get("schema_version", 2),
            strategy_name=strategy.__class__.__name__,
            run_started_at=run_started_at,
        ).set_session_counter(market_feed.get_session_counter())
    """

    communication_server = CommunicationServer()
    websocket_service = WebSocketService(communication_server)
    market_feed_controller = MarketFeedController(market_feed)
    replay_api = ReplayApi(market_feed_controller.handle_action)
    report_export_api = ReportExportApi(report_zip_exporter)
    websocket_message_forwarder = WebSocketMessageForwarder(websocket_service)

    async def run_market_feed():
        market_feed_controller.bind_loop(asyncio.get_running_loop())
        communication_server.register(replay_api)
        communication_server.register(report_export_api)
        communication_server.register(websocket_service)
        communication_server.start()
        for resource in resources.values():
            init_frontend = getattr(resource, "init_frontend", None)
            if callable(init_frontend):
                init_frontend()
        position_manager.init_frontend()
        for analyzer in data_analysis_handler.equity_curve_analyzers:
            analyzer.init_frontend()
        for analyzer in data_analysis_handler.statistics_analyzers:
            analyzer.init_frontend()
        websocket_message_forwarder.complete_initialization()
        print(
            f"A program elindult. "
            f"Replay API: http://{communication_server.host}:{communication_server.port}/api/replay; "
            f"Export API: http://{communication_server.host}:{communication_server.port}/api/export; "
            f"WebSocket: ws://{communication_server.host}:{communication_server.port}/ws. "
            "A market feed stopped állapotban vár."
        )

        await market_feed.run()
        print("A futás befejeződött. A program leállításához nyomjon Ctrl+C-t.")
        await asyncio.Event().wait()

    try:
        asyncio.run(run_market_feed())
    finally:
        try:
            communication_server.stop()
        finally:
            conn.close()