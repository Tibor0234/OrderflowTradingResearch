from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType


def cache_snapshot(message_type: str, data: dict[str, object]) -> None:
    EventBus().emit(
        EventBusMsgType.WEBSOCKET_SNAPSHOT,
        message_type,
        data,
    )
