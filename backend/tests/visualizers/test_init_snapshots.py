from decimal import Decimal

from data_analysis.equity_curve.model import EquityCurve
from data_analysis.statistics.model import Statistics
from data_analysis.utils import AnalysisType
from analyzers.big_trades.model import BigTrades
from analyzers.news.model import News
from analyzers.ohlcv_timeframe.model import OHLCVTimeframe
from analyzers.ohlcv_volume_profile.model import OHLCVVolumeProfile
from analyzers.open_interest.model import OpenInterest
from analyzers.timeframe.candle import Candle
from analyzers.timeframe.model import Timeframe
from analyzers.volume_delta.model import VolumeDelta
from analyzers.volume_profile.model import VolumeProfile
from data_managers.ohlcv.utils import OHLCVCandle, OHLCVMessage, OHLCVPeriod
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.context_chart.ohlcv_timeframe_visualizer import (
    OHLCVTimeframeVisualizer,
)
from visualizers.context_chart.ohlcv_volume_profile_visualizer import (
    OHLCVVolumeProfileVisualizer,
)
from visualizers.data_analysis.equity_curve_visualizer import EquityCurveVisualizer
from visualizers.data_analysis.statistics_visualizer import StatisticsVisualizer
from visualizers.main_chart.big_trades_visualizer import BigTradesVisualizer
from visualizers.main_chart.open_interest_visualizer import OpenInterestVisualizer
from visualizers.main_chart.timeframe_visualizer import TimeframeVisualizer
from visualizers.main_chart.volume_delta_visualizer import VolumeDeltaVisualizer
from visualizers.main_chart.volume_profile_visualizer import VolumeProfileVisualizer
from visualizers.news_panel.news_visualizer import NewsVisualizer
from visualizers.position_panel.position_visualizer import PositionVisualizer


def test_visualizer_init_messages_include_snapshots():
    messages = []
    snapshot_messages = []
    handler = lambda *args: messages.append(args)
    snapshot_handler = lambda *args: snapshot_messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_SNAPSHOT, snapshot_handler)

    timeframe = Timeframe(3)
    timeframe.current = Candle(1, 100)
    timeframe_visualizer = TimeframeVisualizer(timeframe, 1, 60)
    ohlcv_volume_profile = OHLCVVolumeProfile()
    ohlcv_volume_profile.period = OHLCVPeriod.LAST_DAY
    visualizers = [
        timeframe_visualizer,
        VolumeProfileVisualizer(VolumeProfile(4, 70), 1, 3),
        VolumeDeltaVisualizer(VolumeDelta(3), 1, "volume_delta"),
        BigTradesVisualizer(BigTrades(), 1, 5),
        OpenInterestVisualizer(OpenInterest(), 1),
        OHLCVTimeframeVisualizer(
            OHLCVTimeframe(OHLCVPeriod.LAST_DAY),
            1,
        ),
        OHLCVVolumeProfileVisualizer(ohlcv_volume_profile, 1),
        EquityCurveVisualizer(EquityCurve(AnalysisType.CUMULATIVE)),
        StatisticsVisualizer(Statistics(AnalysisType.CUMULATIVE)),
        NewsVisualizer(News()),
        PositionVisualizer([], [], [], []),
    ]
    try:
        for visualizer in visualizers:
            visualizer.init_frontend()

        assert len(messages) == len(visualizers)
        assert all(
            "snapshot" in data
            for message_type, data in messages
            if message_type in {"resource_init", "analysis_init"}
        )
        assert messages[0][1]["snapshot"]["candles"] == [
            {"time": 1, "open": 100, "high": 100, "low": 100, "close": 100}
        ]
        assert messages[-1] == (
            "position_init",
            {"trades": [], "orders": [], "stop_orders": []},
        )

        timeframe.history.append(timeframe.current)
        timeframe.current = Candle(2, 101)
        timeframe_visualizer.on_candle_close(timeframe.history[-1])
        assert snapshot_messages == [
            (
                "resource_init",
                {
                    "resource_type": "timeframe",
                    "target": "main_chart/1",
                    "candle_seconds": 60,
                    "length": 3,
                    "snapshot": {
                        "candles": [
                            {
                                "time": 1,
                                "open": 100,
                                "high": 100,
                                "low": 100,
                                "close": 100,
                            },
                            {
                                "time": 2,
                                "open": 101,
                                "high": 101,
                                "low": 101,
                                "close": 101,
                            },
                        ]
                    },
                },
            )
        ]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)
        event_bus.listeners[EventBusMsgType.WEBSOCKET_SNAPSHOT].remove(
            snapshot_handler
        )


def test_ohlcv_timeframe_update_uses_snapshot_data():
    messages = []
    snapshots = []
    message_handler = lambda *args: messages.append(args)
    snapshot_handler = lambda *args: snapshots.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, message_handler)
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_SNAPSHOT, snapshot_handler)

    candle = OHLCVCandle(
        time=1,
        open=Decimal("10"),
        high=Decimal("12"),
        low=Decimal("9"),
        close=Decimal("11"),
        volume=Decimal("5"),
    )
    model = OHLCVTimeframe(OHLCVPeriod.LAST_DAY)
    model.interval = "1m"
    model.content = [candle]
    visualizer = OHLCVTimeframeVisualizer(model, 2)

    try:
        visualizer.on_message(
            OHLCVMessage(
                period=OHLCVPeriod.LAST_DAY,
                interval="1m",
                candles=[candle],
            )
        )

        assert messages == [
            (
                "market_update",
                {
                    "resource_type": "ohlcv_timeframe",
                    "target": "context_chart/2",
                    "interval": "1m",
                    "candles": [
                        {
                            "time": 1,
                            "open": Decimal("10"),
                            "high": Decimal("12"),
                            "low": Decimal("9"),
                            "close": Decimal("11"),
                        }
                    ],
                },
            )
        ]
        assert snapshots == [
            (
                "resource_init",
                {
                    "resource_type": "ohlcv_timeframe",
                    "target": "context_chart/2",
                    "period": "last_day",
                    "snapshot": {
                        "interval": "1m",
                        "candles": [
                            {
                                "time": 1,
                                "open": Decimal("10"),
                                "high": Decimal("12"),
                                "low": Decimal("9"),
                                "close": Decimal("11"),
                            }
                        ],
                    },
                },
            )
        ]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(
            message_handler
        )
        event_bus.listeners[EventBusMsgType.WEBSOCKET_SNAPSHOT].remove(
            snapshot_handler
        )
