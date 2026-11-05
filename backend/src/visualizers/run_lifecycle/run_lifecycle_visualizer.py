from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from market_feed.utils import SessionCounter


class RunLifecycleVisualizer:
    """Broadcasts visualization updates for run lifecycle events."""

    def __init__(self, strategy_name: str, session_counter: SessionCounter):
        self.strategy_name = strategy_name
        self.session_counter = session_counter
        EventBus().subscribe(
            EventBusMsgType.SESSION_PAIR_START,
            self.on_session_pair_start,
        )
        EventBus().subscribe(
            EventBusMsgType.PROCESS_END,
            self.on_process_end,
        )

    def on_session_pair_start(self) -> None:
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "session_start",
            {
                "strategy_name": self.strategy_name,
                "session_number": self.session_counter.session,
                "symbol": self.session_counter.symbol,
                "progress": (
                    f"{self.session_counter.session_pair_count}/"
                    f"{self.session_counter.selected_session_pairs}"
                ),
            },
        )

    def on_process_end(self) -> None:
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "process_end",
            {}
        )
