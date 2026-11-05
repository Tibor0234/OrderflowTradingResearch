import asyncio
from datetime import datetime

import pytest

from market_feed.feed import MarketFeed


class _Generator:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _SourceCoordinator:
    def __init__(self, generator):
        self.generator = generator

    def initialize_sources(self, _session_pair_id):
        return {
            "trade": {
                "generator": self.generator,
                "item": object(),
            }
        }

    @staticmethod
    def get_active_sources(sources):
        return sources

    @staticmethod
    def select_next_source(_active_sources):
        return "trade"

    @staticmethod
    def advance_source(_sources, _event_type):
        pass


class _EventForwarder:
    @staticmethod
    def forward(_event_type, _item):
        pass


class _EventBus:
    @staticmethod
    def emit(*_args, **_kwargs):
        pass


class _DataProvider:
    @staticmethod
    def set_symbol(_symbol):
        pass


def test_replay_cancellation_closes_source_generators(monkeypatch):
    async def run():
        generator = _Generator()
        feed = object.__new__(MarketFeed)
        feed.database_generator_factory = type(
            "_DatabaseGeneratorFactory",
            (),
            {"instrument_metadata": staticmethod(lambda _session_pair_id: None)},
        )()
        feed.source_coordinator = _SourceCoordinator(generator)
        feed.event_forwarder = _EventForwarder()
        feed._processing = asyncio.Event()
        feed.start()

        monkeypatch.setattr("market_feed.feed.EventBus", _EventBus)
        monkeypatch.setattr("market_feed.feed.DataProvider", _DataProvider)

        replay = asyncio.create_task(
            feed._replay_session_pair((1, 1, "BTCUSDT", datetime.now()))
        )
        await asyncio.sleep(0)
        replay.cancel()

        with pytest.raises(asyncio.CancelledError):
            await replay

        assert generator.closed

    asyncio.run(run())


def test_market_feed_waits_for_start_before_processing(monkeypatch):
    async def run():
        feed = object.__new__(MarketFeed)
        feed._processing = asyncio.Event()
        feed.session_pair_manager = type(
            "_SessionPairManager",
            (),
            {
                "get_next": lambda _self: None,
            },
        )()
        monkeypatch.setattr("market_feed.feed.EventBus", _EventBus)

        replay = asyncio.create_task(feed.run())
        await asyncio.sleep(0)

        assert not replay.done()

        feed.start()
        await replay

    asyncio.run(run())


def test_market_feed_stop_pauses_processing_until_restarted(monkeypatch):
    async def run():
        generator = _Generator()
        feed = object.__new__(MarketFeed)
        feed._processing = asyncio.Event()
        feed.start()
        feed.database_generator_factory = type(
            "_DatabaseGeneratorFactory",
            (),
            {"instrument_metadata": staticmethod(lambda _session_pair_id: None)},
        )()

        source = {
            "generator": generator,
            "item": object(),
            "done": False,
        }

        class _SingleEventSourceCoordinator:
            @staticmethod
            def initialize_sources(_session_pair_id):
                return {"trade": source}

            @staticmethod
            def get_active_sources(sources):
                return {
                    event_type: item
                    for event_type, item in sources.items()
                    if not item["done"]
                }

            @staticmethod
            def select_next_source(_active_sources):
                return "trade"

            @staticmethod
            def advance_source(sources, _event_type):
                sources["trade"]["done"] = True

        forwarded = []

        class _StoppingEventForwarder:
            @staticmethod
            def forward(event_type, _item):
                forwarded.append(event_type)
                feed.stop()

        feed.source_coordinator = _SingleEventSourceCoordinator()
        feed.event_forwarder = _StoppingEventForwarder()
        monkeypatch.setattr("market_feed.feed.EventBus", _EventBus)

        replay = asyncio.create_task(
            feed._replay_session_pair((1, 1, "BTCUSDT", datetime.now()))
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert forwarded == ["trade"]
        assert not replay.done()

        feed.start()
        await replay
        assert generator.closed

    asyncio.run(run())
