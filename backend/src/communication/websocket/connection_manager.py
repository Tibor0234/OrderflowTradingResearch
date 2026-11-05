import asyncio
import logging
import threading
import uuid

from aiohttp import web

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks connected clients and forwards prepared text or binary messages."""

    def __init__(self):
        self._connections: dict[str, web.WebSocketResponse] = {}
        self._initialized_clients: set[str] = set()
        self._pending_messages: dict[str, list[str | bytes]] = {}
        self._lock = threading.Lock()

    @property
    def active_client_ids(self) -> tuple[str, ...]:
        """Return the identifiers of currently connected clients."""
        with self._lock:
            return tuple(self._connections)

    def connect(self, connection: web.WebSocketResponse) -> str:
        """Register a client connection and return its identifier."""
        client_id = uuid.uuid4().hex
        with self._lock:
            self._connections[client_id] = connection
            self._pending_messages[client_id] = []
        logger.info("WebSocket client connected: %s", client_id)
        return client_id

    def disconnect(self, client_id: str) -> None:
        """Remove a client connection if it is still registered."""
        with self._lock:
            removed = self._connections.pop(client_id, None)
            self._initialized_clients.discard(client_id)
            self._pending_messages.pop(client_id, None)
        if removed is not None:
            logger.info("WebSocket client disconnected: %s", client_id)

    async def initialize_client(
        self,
        client_id: str,
        initial_messages: list[str | bytes],
    ) -> bool:
        """Send initial messages before flushing messages queued during setup."""
        with self._lock:
            connection = self._connections.get(client_id)

        if connection is None:
            return False

        try:
            for message in initial_messages:
                await self._send(connection, message)

            while True:
                with self._lock:
                    connection = self._connections.get(client_id)
                    if connection is None:
                        return False

                    pending_messages = self._pending_messages[client_id]
                    self._pending_messages[client_id] = []
                    if not pending_messages:
                        self._initialized_clients.add(client_id)
                        return True

                for message in pending_messages:
                    await self._send(connection, message)
        except (ConnectionResetError, RuntimeError) as error:
            logger.warning(
                "WebSocket initialization send failed for client %s: %s",
                client_id,
                error,
            )
            self.disconnect(client_id)
            return False

    async def send_to_client(self, client_id: str, message: str | bytes) -> bool:
        """Send a prepared message to one connected client."""
        with self._lock:
            connection = self._connections.get(client_id)
            if connection is not None and client_id not in self._initialized_clients:
                self._pending_messages[client_id].append(message)
                return True

        if connection is None:
            return False

        try:
            await self._send(connection, message)
        except (ConnectionResetError, RuntimeError) as error:
            logger.warning("WebSocket send failed for client %s: %s", client_id, error)
            self.disconnect(client_id)
            return False

        return True

    async def close_all(self) -> None:
        """Close all connected WebSocket clients during server shutdown."""
        with self._lock:
            connections = list(self._connections.values())

        await asyncio.gather(
            *(connection.close(code=1001, message=b"Server shutdown") for connection in connections),
            return_exceptions=True,
        )

    @staticmethod
    async def _send(connection: web.WebSocketResponse, message: str | bytes) -> None:
        if isinstance(message, bytes):
            await connection.send_bytes(message)
        else:
            await connection.send_str(message)

    async def broadcast(self, message: str | bytes) -> int:
        """Send a prepared message to each connected client and return successes."""
        client_ids = self.active_client_ids
        sent = await asyncio.gather(
            *(self.send_to_client(client_id, message) for client_id in client_ids)
        )
        return sum(sent)
