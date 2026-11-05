import logging
from collections.abc import Awaitable, Callable

from aiohttp import web

from communication.api.cors import cors_headers, cors_preflight_response

logger = logging.getLogger(__name__)

ReplayActionHandler = Callable[[str], Awaitable[None]]


class ReplayApi:
    """Register the HTTP API for controlling market-data replay."""

    def __init__(self, action_handler: ReplayActionHandler | None = None):
        self._action_handler = action_handler

    def set_action_handler(self, handler: ReplayActionHandler) -> None:
        """Set the callback that applies validated replay actions."""
        self._action_handler = handler

    def register_routes(self, app: web.Application) -> None:
        """Register replay API routes on the shared HTTP application."""
        app.router.add_post("/api/replay", self.handle_replay_action)
        app.router.add_options("/api/replay", self.handle_replay_preflight)

    async def handle_replay_preflight(self, request: web.Request) -> web.Response:
        """Allow browser clients served from localhost to call the replay endpoint."""
        return cors_preflight_response(request, "POST, OPTIONS")

    async def handle_replay_action(self, request: web.Request) -> web.Response:
        """Validate a replay command and return an explicit success or error."""
        headers = cors_headers(request)
        if request.content_type != "application/json":
            return web.json_response(
                {"error": "Content-Type must be application/json"},
                status=400,
                headers=headers,
            )

        try:
            payload = await request.json()
        except ValueError:
            return web.json_response(
                {"error": "Request body must be valid JSON"},
                status=400,
                headers=headers,
            )

        action = payload.get("action") if isinstance(payload, dict) else None
        if action != "start" and action != "stop":
            return web.json_response(
                {"error": "action must be 'start' or 'stop'"},
                status=400,
                headers=headers,
            )

        handler = self._action_handler
        if handler is None:
            return web.json_response(
                {"error": "Replay control is unavailable"},
                status=503,
                headers=headers,
            )

        try:
            await handler(action)
        except Exception:
            logger.exception("Failed to apply replay action %s", action)
            return web.json_response(
                {"error": "Failed to apply replay action"},
                status=500,
                headers=headers,
            )

        return web.json_response({"action": action, "status": "ok"}, headers=headers)
