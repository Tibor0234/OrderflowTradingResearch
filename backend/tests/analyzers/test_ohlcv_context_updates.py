from decimal import Decimal

from data_managers.ohlcv.manager import OHLCVManager
from data_managers.ohlcv.utils import OHLCVPeriod
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from resource_config import ResourceConfig


def test_context_timeframes_and_profiles_share_chart_ids_and_receive_manager_updates():
    resources = ResourceConfig()._build_resources()
    ResourceConfig()._setup_resources(resources)
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    manager = OHLCVManager()

    try:
        for resource in resources.values():
            if hasattr(resource, "period") and resource.period in (
                OHLCVPeriod.LAST_DAY,
                OHLCVPeriod.LAST_WEEK,
            ):
                manager.subscribe(resource)

        last_day = resources["ohlcv_last_day"]
        last_day_profile = resources["ohlcv_last_day_vp"]
        last_week = resources["ohlcv_last_week"]

        assert resources["tf_1m"].chart_id == last_day.chart_id == 0
        assert last_day_profile.chart_id == 0
        assert last_day_profile.period == last_day.period == OHLCVPeriod.LAST_DAY
        assert last_week.chart_id == 1
        assert resources["ohlcv_last_week_vp"].period == last_week.period == OHLCVPeriod.LAST_WEEK

        for resource in resources.values():
            init_frontend = getattr(resource, "init_frontend", None)
            if callable(init_frontend):
                init_frontend()

        manager.forward_message({
            "period": OHLCVPeriod.LAST_DAY.value,
            "interval": "1h",
            "candles": [
                {
                    "open_time": 1_000,
                    "open": "10",
                    "high": "20",
                    "low": "10",
                    "close": "15",
                    "volume": "100",
                },
            ],
        })

        assert last_day.model.content[0].close == Decimal("15")
        assert last_day_profile.model.start_time == 1_000
        assert any(
            message_type == "market_update"
            and message_data["resource_type"] == "ohlcv_timeframe"
            and message_data["target"] == "context_chart/0"
            for message_type, message_data in messages
        )
        assert any(
            message_type == "market_update"
            and message_data["resource_type"] == "ohlcv_volume_profile"
            and message_data["target"] == "context_chart/0"
            for message_type, message_data in messages
        )
        init_message = next(
            message_data
            for message_type, message_data in messages
            if message_type == "resource_init"
            and message_data["resource_type"] == "ohlcv_timeframe"
        )
        assert init_message == {
            "resource_type": "ohlcv_timeframe",
            "target": "context_chart/0",
            "period": OHLCVPeriod.LAST_DAY.value,
        }
        update_message = next(
            message_data
            for message_type, message_data in messages
            if message_type == "market_update"
            and message_data["resource_type"] == "ohlcv_timeframe"
        )
        assert update_message["interval"] == "1h"
        assert any(
            message_type == "resource_init"
            and message_data["resource_type"] == "ohlcv_timeframe"
            and message_data["target"] == "context_chart/0"
            for message_type, message_data in messages
        )
        assert last_week.model.content == []
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)
