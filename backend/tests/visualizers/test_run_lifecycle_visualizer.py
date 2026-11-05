from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from market_feed.utils import SessionCounter
from visualizers.run_lifecycle.run_lifecycle_visualizer import RunLifecycleVisualizer


def test_run_lifecycle_visualizer_sends_strategy_session_symbol_and_progress():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    counter = SessionCounter(
        session=42,
        symbol="BTCUSDT",
        session_pair_count=7,
        selected_session_pairs=42,
    )
    visualizer = RunLifecycleVisualizer("TestStrategy", counter)

    try:
        assert visualizer.on_session_pair_start in event_bus.listeners[
            EventBusMsgType.SESSION_PAIR_START
        ]
        visualizer.on_session_pair_start()

        assert messages == [
            (
                "session_start",
                {
                    "strategy_name": "TestStrategy",
                    "session_number": 42,
                    "symbol": "BTCUSDT",
                    "progress": "7/42",
                },
            )
        ]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)
        event_bus.listeners[EventBusMsgType.SESSION_PAIR_START].remove(
            visualizer.on_session_pair_start
        )
