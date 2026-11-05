import asyncio

import pytest

from market_feed.controller import MarketFeedController


class _MarketFeed:
    def __init__(self):
        self.actions = []
        self.action_loops = []

    def start(self):
        self.actions.append("start")
        self.action_loops.append(asyncio.get_running_loop())

    def stop(self):
        self.actions.append("stop")
        self.action_loops.append(asyncio.get_running_loop())


def test_controller_applies_actions_on_the_bound_feed_loop():
    async def run():
        market_feed = _MarketFeed()
        controller = MarketFeedController(market_feed)
        loop = asyncio.get_running_loop()
        controller.bind_loop(loop)

        await controller.handle_action("start")
        await controller.handle_action("stop")

        assert market_feed.actions == ["start", "stop"]
        assert market_feed.action_loops == [loop, loop]

    asyncio.run(run())


def test_controller_rejects_actions_before_it_is_bound():
    async def run():
        controller = MarketFeedController(_MarketFeed())
        with pytest.raises(RuntimeError, match="not bound"):
            await controller.handle_action("start")

    asyncio.run(run())


def test_controller_rejects_unknown_actions():
    async def run():
        controller = MarketFeedController(_MarketFeed())
        controller.bind_loop(asyncio.get_running_loop())
        with pytest.raises(ValueError, match="action must"):
            await controller.handle_action("pause")

    asyncio.run(run())
