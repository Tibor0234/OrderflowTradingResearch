from decimal import Decimal

from analyzers.big_trades.analyzer import BigTradesAnalyzer
from analyzers.open_interest.analyzer import OpenInterestAnalyzer
from analyzers.volume_profile.analyzer import VolumeProfileAnalyzer
from data_managers.open_interest.utils import OpenInterestMessage
from data_managers.trade.utils import TradeMessage
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from trading.market_entities.utils import Side


def test_open_interest_aggregates_until_timeframe_close():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    analyzer = OpenInterestAnalyzer()
    analyzer.bind_to_timeframe(100, 7)

    try:
        analyzer.process_message(OpenInterestMessage(1_000, Decimal("10")))
        analyzer.process_message(OpenInterestMessage(2_000, Decimal("12")))
        analyzer.on_candle_close(60_000)

        assert len(analyzer.model.history) == 1
        assert analyzer.model.history[-1].value == Decimal("11")
        assert messages[-1][0] == "market_update"
        assert messages[-1][1]["resource_type"] == "open_interest"
        assert messages[-1][1]["target"] == "main_chart/7"

        analyzer.process_message(OpenInterestMessage(61_000, Decimal("15")))
        analyzer.process_message(OpenInterestMessage(62_000, Decimal("17")))
        analyzer.on_candle_close(120_000)

        assert len(analyzer.model.history) == 2
        assert analyzer.model.history[-1].value == Decimal("16")
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_big_trades_emits_accumulated_trades_on_candle_close():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    analyzer = BigTradesAnalyzer(top_pct=100)
    analyzer.bind_to_timeframe(100, 3)

    try:
        analyzer.process_message(
            TradeMessage(1, Decimal("10"), Decimal("1"), Side.BUY)
        )
        analyzer.process_message(
            TradeMessage(2, Decimal("11"), Decimal("2"), Side.BUY)
        )
        analyzer.on_candle_close(60_000)

        assert messages[-1][0] == "market_update"
        assert messages[-1][1]["resource_type"] == "big_trades"
        assert messages[-1][1]["target"] == "main_chart/3"
        assert messages[-1][1]["trades"] == [{
            "time": 2,
            "price": Decimal("11"),
            "quantity": Decimal("2"),
            "side": 1,
        }]

        analyzer.on_candle_close(120_000)
        assert messages[-1][1]["trades"] == [{
            "time": 2,
            "price": Decimal("11"),
            "quantity": Decimal("2"),
            "side": 1,
        }]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_volume_profile_emits_init_and_profile_snapshot():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    analyzer = VolumeProfileAnalyzer(price_bin_count=4, value_area_pct=70, length=5)
    analyzer.bind_to_timeframe(100, 2)

    try:
        analyzer.init_frontend()
        analyzer.process_message(
            TradeMessage(1, Decimal("10"), Decimal("2"), Side.BUY)
        )
        analyzer.process_message(
            TradeMessage(2, Decimal("20"), Decimal("3"), Side.SELL)
        )
        analyzer.on_candle_close(60_000)

        assert messages[0] == (
            "resource_init",
            {
                "resource_type": "volume_profile",
                "target": "main_chart/2",
                "price_bin_count": 4,
                "value_area_pct": 70,
                "length": 5,
                "snapshot": {
                    "time": None,
                    "bins": [],
                    "poc": None,
                    "value_area": None,
                },
            },
        )
        update_type, update = messages[1]
        assert update_type == "market_update"
        assert update["resource_type"] == "volume_profile"
        assert update["target"] == "main_chart/2"
        assert update["time"] == 60_000
        assert len(update["bins"]) == 4
        assert update["poc"] is not None
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)
