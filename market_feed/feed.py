from psycopg import Connection

from data_managers.ohlcv.manager import OHLCVManager
from data_managers.news.manager import NewsManager
from data_managers.order_book.manager import OrderBookManager
from data_managers.open_interest.manager import OpenInterestManager
from data_managers.trade.manager import TradeManager

from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType

from market_feed.session_pair_manager import SessionPairManager
from market_feed.database_generator_factory import DatabaseGeneratorFactory
from market_feed.source_coordinator import SourceCoordinator
from market_feed.event_forwarder import EventForwarder
from session_pairs.utils import InstrumentMetadata


class MarketFeed:
    """Coordinates market data replay from database across session pairs."""

    def __init__(
        self,
        conn: Connection,
        open_interest_manager: OpenInterestManager,
        orderbook_manager: OrderBookManager,
        trade_manager: TradeManager,
        news_manager: NewsManager,
        ohlcv_manager: OHLCVManager,
        session_numbers: list[int | str] | None = None,
        symbols: list[str] | None = None,
    ):
        """Initialize the market feed and its replay components."""
        self.session_pair_manager = SessionPairManager(
            conn,
            session_numbers=session_numbers,
            symbols=symbols,
        )
        
        self.database_generator_factory = DatabaseGeneratorFactory(conn)
        self.source_coordinator = SourceCoordinator(
            self.database_generator_factory
        )
        
        self.event_forwarder = EventForwarder(
            open_interest_manager,
            orderbook_manager,
            trade_manager,
            ohlcv_manager,
            news_manager,
        )

    @property
    def session_counter(self):
        """Return the session counter used to track replay progress."""
        return self.session_pair_manager.get_counter()

    async def run(self):
        """Replay all available session pairs in sequence."""
        while True:
            session_pair = self.session_pair_manager.get_next()

            if session_pair is None:
                print("Process ended.")
                EventBus().emit(EventBusMsgType.PROCESS_END)
                return

            DataProvider().set_symbol(self.session_pair_manager.counter.symbol)

            await self._replay_session_pair(session_pair)

    async def _replay_session_pair(self, session_pair):
        """Replay all market data sources for a single session pair."""
        session_pair_id, session_id, pair, created_at = session_pair

        print(
            pair.upper(),
            "session pair",
            session_pair_id,
            "| session",
            session_id
        )

        metadata_row = self.database_generator_factory.instrument_metadata(
            session_pair_id
        )
        instrument_metadata = (
            InstrumentMetadata(*metadata_row)
            if metadata_row is not None
            else None
        )
        EventBus().emit(EventBusMsgType.SESSION_PAIR_START)
        EventBus().emit(
            EventBusMsgType.SESSION_PAIR_METADATA,
            instrument_metadata=instrument_metadata
        )

        sources = self.source_coordinator.initialize_sources(session_pair_id)

        while True:
            active_sources = self.source_coordinator.get_active_sources(sources)

            if not active_sources:
                break

            selected_event_type = self.source_coordinator.select_next_source(
                active_sources
            )

            item = sources[selected_event_type]["item"]

            self.event_forwarder.forward(selected_event_type, item)

            self.source_coordinator.advance_source(sources, selected_event_type)

        EventBus().emit(EventBusMsgType.SESSION_PAIR_END)