from decimal import Decimal

from data_analysis.statistics.model import Statistics
from data_analysis.utils import AnalysisType
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.data_analysis.statistics_visualizer import StatisticsVisualizer


def test_statistics_visualizer_initializes_and_sends_model_updates():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    model = Statistics(
        type=AnalysisType.CUMULATIVE,
        symbol="BTCUSDT",
        starting_balance=Decimal("1000"),
        equity=Decimal("1100"),
        total_trades=1,
        winrate=0.5,
        average_trade_duration=12.5,
        pnl=Decimal("25"),
        fees_paid=Decimal("1.5"),
        roi=Decimal("0.1"),
        profit_factor=2.5,
    )
    visualizer = StatisticsVisualizer(model)

    try:
        visualizer.init_frontend()
        visualizer.on_statistics_update()

        assert messages[0] == (
            "analysis_init",
            {
                "analysis_type": "statistics",
                "target": "statistics/cumulative_BTCUSDT",
                "name": "BTCUSDT",
                "snapshot": {
                    "total_trades": 1,
                    "winrate": "0.5",
                    "pnl": "25",
                    "roi": "0.1",
                    "max_drawdown": "0",
                    "average_trade_duration": 12.5,
                },
            },
        )
        assert messages[1] == (
            "analysis_update",
            {
                "analysis_type": "statistics",
                "target": "statistics/cumulative_BTCUSDT",
                "statistics": {
                    "total_trades": 1,
                    "winrate": "0.5",
                    "pnl": "25",
                    "roi": "0.1",
                    "max_drawdown": "0",
                    "average_trade_duration": 12.5,
                },
            },
        )
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)
