from enum import Enum

class EventBusMsgType(Enum):
    """Defines the event types supported by the event bus."""
    
    SESSION_PAIR_START = 'session_pair_start'
    SESSION_PAIR_END = 'session_pair_end'
    PROCESS_END = 'process_end'
    
    SESSION_PAIR_METADATA = 'session_pair_metadata'
    
    CANDLE_CLOSE = 'candle_close'
    BIG_TRADE = 'big_trade'
    TRADE_CLOSE = 'trade_close'

    PRICE_UPDATE = 'price_update'
    TRADE_ADDED = 'trade_added'
    TRADE_REMOVED = 'trade_removed'