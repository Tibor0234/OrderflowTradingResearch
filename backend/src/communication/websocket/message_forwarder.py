import asyncio
import json
import logging
import threading
from concurrent.futures import Future
from typing import Any

from communication.websocket.service import WebSocketService
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType

logger = logging.getLogger(__name__)


class WebSocketMessageForwarder:
    """Wrap application events as WebSocket messages and forward them asynchronously."""

    _INITIALIZATION_MESSAGE_TYPES = {
        "resource_init",
        "analysis_init",
        "position_init",
        "session_start",
    }

    def __init__(self, websocket_service: WebSocketService):
        self._websocket_service = websocket_service
        self._initialization_messages: dict[
            tuple[str, str | None, str | None], str
        ] = {}
        self._initialization_lock = threading.Lock()
        self._initialization_complete: Future[None] = Future()
        self._websocket_service.set_client_snapshot_provider(
            self._get_initialization_snapshot
        )
        EventBus().subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, self.forward)
        EventBus().subscribe(EventBusMsgType.WEBSOCKET_SNAPSHOT, self.cache_snapshot)

    def forward(self, message_type: str, data: Any) -> None:
        """Wrap an event payload and schedule it for broadcast without blocking."""
        message = self._serialize(message_type, data)
        if message_type in self._INITIALIZATION_MESSAGE_TYPES:
            with self._initialization_lock:
                self._initialization_messages[
                    self._initialization_key(message_type, data)
                ] = message
                should_broadcast = self._initialization_complete.done()
            if not should_broadcast:
                return

        try:
            delivery = self._websocket_service.broadcast(message)
        except RuntimeError:
            logger.exception("Could not schedule WebSocket message broadcast")
            return

        delivery.add_done_callback(self._log_delivery_result)

    def cache_snapshot(self, message_type: str, data: Any) -> None:
        """Replace an initialization message without broadcasting it."""
        if message_type not in self._INITIALIZATION_MESSAGE_TYPES:
            raise ValueError(f"Unsupported WebSocket snapshot type: {message_type}")

        message = self._serialize(message_type, data)
        with self._initialization_lock:
            self._initialization_messages[
                self._initialization_key(message_type, data)
            ] = message

    def complete_initialization(self) -> None:
        """Allow newly connected clients to receive the completed init snapshot."""
        if not self._initialization_complete.done():
            self._initialization_complete.set_result(None)

    async def _get_initialization_snapshot(self) -> list[str]:
        if not self._initialization_complete.done():
            await asyncio.wrap_future(self._initialization_complete)

        with self._initialization_lock:
            session_start = self._initialization_messages.get(
                ("session_start", None, None)
            )
            messages = [
                message
                for key, message in self._initialization_messages.items()
                if key[0] != "session_start"
            ]
            if session_start is not None:
                messages.append(session_start)
            return messages

    @classmethod
    def _serialize(cls, message_type: str, data: Any) -> str:
        if message_type in cls._INITIALIZATION_MESSAGE_TYPES:
            if not isinstance(data, dict):
                raise TypeError(f"{message_type} data must be a dictionary")
            if message_type in {"resource_init", "analysis_init"}:
                type_field = (
                    "analysis_type"
                    if message_type == "analysis_init"
                    else "resource_type"
                )
                if not isinstance(data.get(type_field), str):
                    raise ValueError(f"{message_type} data must include {type_field}")
                if not isinstance(data.get("target"), str):
                    raise ValueError(f"{message_type} data must include target")

        return json.dumps(
            {"type": message_type, "data": data},
            default=str,
            separators=(",", ":"),
        )

    @staticmethod
    def _initialization_key(
        message_type: str,
        data: dict[str, Any],
    ) -> tuple[str, str | None, str | None]:
        target = data.get("target")
        type_field = (
            "resource_type"
            if message_type == "resource_init"
            else "analysis_type"
            if message_type == "analysis_init"
            else None
        )
        resource_type = data.get(type_field) if type_field is not None else None
        return (
            message_type,
            target if isinstance(target, str) else None,
            resource_type if isinstance(resource_type, str) else None,
        )

    @staticmethod
    def _log_delivery_result(delivery: Future[int]) -> None:
        if delivery.cancelled():
            logger.warning("WebSocket message broadcast was cancelled")
            return

        error = delivery.exception()
        if error is not None:
            logger.error(
                "WebSocket message broadcast failed",
                exc_info=(type(error), error, error.__traceback__),
            )
