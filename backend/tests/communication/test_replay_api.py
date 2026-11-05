import asyncio
import json

import aiohttp

from communication.api import ReplayApi
from communication.server import CommunicationServer
from communication.websocket.service import WebSocketService


def test_replay_api_applies_start_and_stop_actions():
    server = CommunicationServer(port=0)
    actions = []

    async def handle_action(action):
        actions.append(action)

    server.register(ReplayApi(handle_action))
    server.register(WebSocketService(server))
    server.start()

    async def send_actions():
        async with aiohttp.ClientSession() as session:
            for action in ("start", "stop"):
                async with session.post(
                    f"http://{server.host}:{server.port}/api/replay",
                    json={"action": action},
                ) as response:
                    assert response.status == 200
                    assert await response.json() == {
                        "action": action,
                        "status": "ok",
                    }

    try:
        asyncio.run(send_actions())
    finally:
        server.stop()

    assert actions == ["start", "stop"]


def test_replay_api_rejects_invalid_actions_without_applying_them():
    server = CommunicationServer(port=0)
    server.register(ReplayApi(lambda _action: asyncio.sleep(0)))
    server.start()

    async def send_invalid_action():
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{server.host}:{server.port}/api/replay",
                data=json.dumps({"action": "pause"}),
                headers={"Content-Type": "application/json"},
            ) as response:
                assert response.status == 400
                assert "start" in (await response.json())["error"]

    try:
        asyncio.run(send_invalid_action())
    finally:
        server.stop()
