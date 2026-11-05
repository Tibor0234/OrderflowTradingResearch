import asyncio
import logging
import threading
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any, Protocol, TypeVar

from aiohttp import web

logger = logging.getLogger(__name__)

Result = TypeVar("Result")


class CommunicationService(Protocol):
    """A service that registers HTTP routes on the shared application."""

    def register_routes(self, app: web.Application) -> None:
        """Register this service's routes and lifecycle callbacks."""


class CommunicationServer:
    """Run registered HTTP and WebSocket services on one shared listener."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._services: list[CommunicationService] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._shutdown: asyncio.Event | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._startup_error: Exception | None = None

    def register(self, service: CommunicationService) -> None:
        """Register a service before the server starts."""
        if self._thread is not None:
            raise RuntimeError("Cannot register services after the server starts")
        self._services.append(service)

    def start(self, timeout: float = 10) -> None:
        """Start the server thread and wait until it accepts connections."""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Communication server is already running")

        self._ready.clear()
        self._startup_error = None
        self._thread = threading.Thread(
            target=self._run,
            name="communication-server",
            daemon=True,
        )
        self._thread.start()

        if not self._ready.wait(timeout):
            self.stop()
            raise TimeoutError("Communication server did not start before the timeout")
        if self._startup_error is not None:
            raise RuntimeError("Communication server failed to start") from self._startup_error

    def stop(self, timeout: float = 10) -> None:
        """Stop the server and wait for its event loop thread to finish."""
        thread = self._thread
        loop = self._loop
        shutdown = self._shutdown

        if thread is None:
            return
        if loop is not None and shutdown is not None and loop.is_running():
            loop.call_soon_threadsafe(shutdown.set)

        thread.join(timeout)
        if thread.is_alive():
            raise TimeoutError("Communication server did not stop before the timeout")

        self._thread = None
        self._loop = None
        self._shutdown = None

    def submit(self, coroutine: Coroutine[Any, Any, Result]) -> Future[Result]:
        """Schedule a coroutine on the server loop from another thread."""
        loop = self._loop
        if loop is None or not loop.is_running():
            coroutine.close()
            raise RuntimeError("Communication server is not running")
        return asyncio.run_coroutine_threadsafe(coroutine, loop)

    def _run(self) -> None:
        try:
            asyncio.run(self._serve())
        except Exception as error:
            self._startup_error = error
            self._ready.set()
            logger.exception("Communication server stopped unexpectedly")

    async def _serve(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._shutdown = asyncio.Event()

        app = web.Application()
        for service in self._services:
            service.register_routes(app)

        runner = web.AppRunner(app)
        try:
            await runner.setup()
            site = web.TCPSite(runner, self.host, self.port)
            await site.start()
            if site._server is not None and site._server.sockets:
                self.port = int(site._server.sockets[0].getsockname()[1])
            self._ready.set()
            await self._shutdown.wait()
        finally:
            await runner.cleanup()
