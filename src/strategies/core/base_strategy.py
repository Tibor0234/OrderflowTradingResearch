from abc import ABC
from trading.market_entities.trade import Trade
from strategies.core.framework import StrategyFramework
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from data_managers.trade.utils import TradeMessage

class BaseStrategy(ABC):
    """Defines the base interface for event-driven trading strategies."""

    def init(self, framework: StrategyFramework):
        """Initialize the strategy with its framework and event subscriptions."""
        self.fw = framework

        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_START, self.on_session_pair_start)
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_END, self.on_session_pair_end)
        EventBus().subscribe(EventBusMsgType.PRICE_UPDATE, self.on_price_update)
        EventBus().subscribe(EventBusMsgType.CANDLE_CLOSE, self.on_candle_close)
        EventBus().subscribe(EventBusMsgType.TRADE_CLOSE, self.on_trade_close)

    #on signal metódusok
    def on_session_pair_start(self):
        """Handle the start of a new session pair."""
        pass

    def on_session_pair_end(self):
        """Handle the end of the current session pair."""
        pass

    def on_price_update(self):
        """Handle a price update event."""
        pass

    def on_candle_close(self, candle_sec: int):
        """Handle the close of a candle."""
        pass

    def on_big_trade(self, msg: TradeMessage, top_pct: float):
        """Handle a big trade event."""
        pass

    def on_trade_close(self, trade: Trade):
        """Handle the close of a trade."""
        pass