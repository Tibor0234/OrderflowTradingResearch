import asyncio

from market_feed.feed import MarketFeed


class MarketFeedController:
    """Apply replay control actions on the market feed's event loop."""

    def __init__(self, market_feed: MarketFeed):
        self._market_feed = market_feed
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the controller to the event loop that runs the market feed."""
        if not loop.is_running():
            raise RuntimeError("Market feed event loop must be running")
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError("Market feed controller is already bound to another loop")
        self._loop = loop

    async def handle_action(self, action: str) -> None:
        """Apply a start or stop action on the market feed's event loop."""
        if action != "start" and action != "stop":
            raise ValueError("action must be 'start' or 'stop'")

        loop = self._loop
        if loop is None or not loop.is_running():
            raise RuntimeError("Market feed controller is not bound to a running loop")

        await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(self._apply_action(action), loop)
        )

    async def _apply_action(self, action: str) -> None:
        if action == "start":
            self._market_feed.start()
        else:
            self._market_feed.stop()
