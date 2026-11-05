import asyncio
import json

import websockets

from communication.websocket.message_forwarder import WebSocketMessageForwarder
from communication.server import CommunicationServer
from communication.websocket.service import WebSocketService
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType


def test_each_client_gets_snapshot_before_updates():
    server = CommunicationServer(port=0)
    websocket_service = WebSocketService(server)
    server.register(websocket_service)
    forwarder = WebSocketMessageForwarder(websocket_service)
    server.start()

    async def wait_for_clients(count):
        for _ in range(1000):
            if len(websocket_service.active_client_ids) >= count:
                return
            await asyncio.sleep(0.001)
        raise AssertionError(f"Expected {count} connected clients")

    async def run_clients():
        async with websockets.connect(f"ws://{server.host}:{server.port}/ws") as first:
            await wait_for_clients(1)

            queued_update = websocket_service.broadcast(
                json.dumps({"type": "market_update", "data": {"value": 1}})
            )
            assert await asyncio.wait_for(asyncio.wrap_future(queued_update), 1) == 1

            forwarder.complete_initialization()

            first_init = json.loads(await asyncio.wait_for(first.recv(), 1))
            first_volume_profile_init = json.loads(
                await asyncio.wait_for(first.recv(), 1)
            )
            first_analysis_init = json.loads(await asyncio.wait_for(first.recv(), 1))
            first_position_init = json.loads(await asyncio.wait_for(first.recv(), 1))
            first_session_start = json.loads(await asyncio.wait_for(first.recv(), 1))
            first_update = json.loads(await asyncio.wait_for(first.recv(), 1))
            assert first_init["type"] == "resource_init"
            assert first_volume_profile_init["type"] == "resource_init"
            assert first_volume_profile_init["data"]["resource_type"] == "volume_profile"
            assert first_analysis_init["type"] == "analysis_init"
            assert first_position_init["type"] == "position_init"
            assert first_session_start["type"] == "session_start"
            assert first_position_init["data"] == {
                "trades": [],
                "orders": [],
                "stop_orders": [],
            }
            assert first_update["type"] == "market_update"

            forwarder.forward(
                "resource_init",
                {"resource_type": "equity_curve", "target": "data_analysis/equity_curve"},
            )
            late_init = json.loads(await asyncio.wait_for(first.recv(), 1))
            assert late_init["type"] == "resource_init"
            assert late_init["data"]["target"] == "data_analysis/equity_curve"

            forwarder.forward(
                "analysis_init",
                {"analysis_type": "equity_curve", "target": "equity_curve/late"},
            )
            late_analysis_init = json.loads(await asyncio.wait_for(first.recv(), 1))
            assert late_analysis_init["type"] == "analysis_init"
            assert late_analysis_init["data"]["target"] == "equity_curve/late"

            latest_session_start = {
                "strategy_name": "TestStrategy",
                "session_number": 2,
                "symbol": "ETHUSDT",
                "progress": "2/10",
            }
            forwarder.forward("session_start", latest_session_start)
            session_start_update = json.loads(await asyncio.wait_for(first.recv(), 1))
            assert session_start_update == {
                "type": "session_start",
                "data": latest_session_start,
            }
            latest_snapshot = {
                "candles": [{"time": 2, "open": 1, "high": 2, "low": 1, "close": 2}]
            }
            forwarder.cache_snapshot(
                "resource_init",
                {
                    "resource_type": "timeframe",
                    "target": "main_chart/0",
                    "snapshot": latest_snapshot,
                },
            )

            async with websockets.connect(
                f"ws://{server.host}:{server.port}/ws"
            ) as second:
                await wait_for_clients(2)
                second_init = json.loads(await asyncio.wait_for(second.recv(), 1))
                assert second_init["type"] == "resource_init"
                assert second_init["data"]["target"] == "main_chart/0"
                assert second_init["data"]["snapshot"] == latest_snapshot
                second_volume_profile_init = json.loads(
                    await asyncio.wait_for(second.recv(), 1)
                )
                assert second_volume_profile_init["type"] == "resource_init"
                assert (
                    second_volume_profile_init["data"]["resource_type"]
                    == "volume_profile"
                )
                second_analysis_init = json.loads(await asyncio.wait_for(second.recv(), 1))
                assert second_analysis_init["type"] == "analysis_init"
                assert second_analysis_init["data"]["target"] == "equity_curve/initial"
                second_position_init = json.loads(
                    await asyncio.wait_for(second.recv(), 1)
                )
                assert second_position_init["type"] == "position_init"
                assert second_position_init["data"] == {
                    "trades": [],
                    "orders": [],
                    "stop_orders": [],
                }
                second_late_init = json.loads(await asyncio.wait_for(second.recv(), 1))
                assert second_late_init["type"] == "resource_init"
                assert second_late_init["data"]["target"] == "data_analysis/equity_curve"
                second_late_analysis_init = json.loads(
                    await asyncio.wait_for(second.recv(), 1)
                )
                assert second_late_analysis_init["type"] == "analysis_init"
                assert second_late_analysis_init["data"]["target"] == "equity_curve/late"
                second_session_start = json.loads(
                    await asyncio.wait_for(second.recv(), 1)
                )
                assert second_session_start == {
                    "type": "session_start",
                    "data": latest_session_start,
                }

                update = websocket_service.broadcast(
                    json.dumps({"type": "market_update", "data": {"value": 2}})
                )
                assert await asyncio.wait_for(asyncio.wrap_future(update), 1) == 2

                first_next, second_next = await asyncio.gather(
                    asyncio.wait_for(first.recv(), 1),
                    asyncio.wait_for(second.recv(), 1),
                )
                assert json.loads(first_next)["type"] == "market_update"
                assert json.loads(second_next)["type"] == "market_update"

    try:
        forwarder.forward(
            "resource_init",
            {"resource_type": "timeframe", "target": "main_chart/0"},
        )
        forwarder.forward(
            "resource_init",
            {"resource_type": "volume_profile", "target": "main_chart/0"},
        )
        forwarder.forward(
            "analysis_init",
            {"analysis_type": "equity_curve", "target": "equity_curve/initial"},
        )
        forwarder.forward(
            "position_init",
            {"trades": [], "orders": [], "stop_orders": []},
        )
        forwarder.forward(
            "session_start",
            {
                "strategy_name": "TestStrategy",
                "session_number": 1,
                "symbol": "BTCUSDT",
                "progress": "1/10",
            },
        )
        asyncio.run(run_clients())
    finally:
        server.stop()
        EventBus().listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(
            forwarder.forward
        )
        EventBus().listeners[EventBusMsgType.WEBSOCKET_SNAPSHOT].remove(
            forwarder.cache_snapshot
        )
