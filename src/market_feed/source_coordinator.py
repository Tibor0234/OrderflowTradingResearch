from market_feed.utils import EventType
from market_feed.database_generator_factory import DatabaseGeneratorFactory
from market_feed.message_extractor import MessageExtractor


class SourceCoordinator:
    """Coordinates multiple market data sources by timestamp."""

    def __init__(self, generator_factory: DatabaseGeneratorFactory):
        """Initialize the coordinator with a database generator factory."""
        self.generator_factory = generator_factory
        self.extractor = MessageExtractor()

    def initialize_sources(self, session_pair_id):
        """Initialize all data sources for the specified session pair."""
        sources = {}
        generator_methods = {
            EventType.TR: self.generator_factory.trade_generator,
            EventType.OB: self.generator_factory.orderbook_generator,
            EventType.OI: self.generator_factory.oi_generator,
            EventType.OHLCV: self.generator_factory.ohlcv_generator,
            EventType.NWS: self.generator_factory.news_generator,
        }

        for event_type, method in generator_methods.items():
            generator = method(session_pair_id)
            try:
                sources[event_type] = {
                    "generator": generator,
                    "item": next(generator)
                }
            except StopIteration:
                pass

        return sources

    def get_active_sources(self, sources):
        """Return sources that currently have an available item."""
        return {
            event_type: source
            for event_type, source in sources.items()
            if source["item"] is not None
        }

    def select_next_source(self, active_sources):
        """Return the source containing the item with the earliest timestamp."""
        if not active_sources:
            return None

        return min(
            active_sources,
            key=lambda event_type: self.extractor.extract_timestamp(
                active_sources[event_type]["item"]
            )
        )

    def advance_source(self, sources, event_type):
        """Advance the specified source to its next item."""
        try:
            sources[event_type]["item"] = next(
                sources[event_type]["generator"]
            )
        except StopIteration:
            sources[event_type]["item"] = None
