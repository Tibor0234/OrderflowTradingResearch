import logging
from collections.abc import Awaitable, Callable
from concurrent.futures import Future

from aiohttp import WSMsgType, web

from communication.server import CommunicationServer
from communication.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

ClientSnapshotProvider = Callable[[], Awaitable[list[str | bytes]]]


class WebSocketService:
    """Register and manage the application's WebSocket endpoint."""

    def __init__(self, server: CommunicationServer):
        self._server = server
        self.connections = ConnectionManager()
        self._client_snapshot_provider: ClientSnapshotProvider | None = None

    @property
    def active_client_ids(self) -> tuple[str, ...]:
        """Return the identifiers of currently connected clients."""
        return self.connections.active_client_ids

    def set_client_snapshot_provider(self, provider: ClientSnapshotProvider) -> None:
        """Set the provider for messages that initialize each new client."""
        self._client_snapshot_provider = provider

    def send_to_client(self, client_id: str, message: str | bytes) -> Future[bool]:
        """Schedule a prepared message to one client from any backend thread."""
        return self._server.submit(
            self.connections.send_to_client(client_id, message)
        )

    def broadcast(self, message: str | bytes) -> Future[int]:
        """Schedule an explicit broadcast and return the number of successful sends."""
        return self._server.submit(self.connections.broadcast(message))

    def register_routes(self, app: web.Application) -> None:
        """Register the WebSocket endpoint and its shutdown callback."""
        app.router.add_get("/ws", self.handle_connection)
        app.on_shutdown.append(self._close_connections)

    async def handle_connection(self, request: web.Request) -> web.WebSocketResponse:
        """Handle the WebSocket endpoint lifecycle."""
        connection = web.WebSocketResponse()
        await connection.prepare(request)

        client_id = self.connections.connect(connection)
        try:
            if self._client_snapshot_provider is not None:
                initial_messages = await self._client_snapshot_provider()
            else:
                initial_messages = []

            if not await self.connections.initialize_client(client_id, initial_messages):
                return connection

            async for message in connection:
                if message.type == WSMsgType.ERROR:
                    logger.warning(
                        "WebSocket client %s failed: %s",
                        client_id,
                        connection.exception(),
                    )
                    break
        except (ConnectionResetError, RuntimeError) as error:
            logger.debug("WebSocket connection closed for client %s: %s", client_id, error)
        finally:
            self.connections.disconnect(client_id)
        return connection

    async def _close_connections(self, _app: web.Application) -> None:
        await self.connections.close_all()
