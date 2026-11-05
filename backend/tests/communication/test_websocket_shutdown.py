import asyncio

import websockets

from communication.server import CommunicationServer
from communication.websocket.service import WebSocketService


def test_stop_closes_connected_clients_and_server_thread():
    server = CommunicationServer(port=0)
    server.register(WebSocketService(server))
    server.start()
    server_thread = server._thread
    server_loop = server._loop

    async def connect_and_stop():
        async with websockets.connect(
            f"ws://{server.host}:{server.port}/ws"
        ) as connection:
            await asyncio.to_thread(server.stop)
            assert connection.close_code == 1001

    asyncio.run(connect_and_stop())

    assert server._thread is None
    assert server._loop is None
    assert not server_thread.is_alive()
    assert server_loop.is_closed()
