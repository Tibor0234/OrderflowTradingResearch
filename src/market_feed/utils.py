from enum import Enum
from dataclasses import dataclass

class EventType(Enum):
    """Defines the supported market data source types."""

    OI = 'api_oi'
    OB = 'api_ob'
    TR = 'ws_tr'
    NWS = 'nws'
    OHLCV = 'ohlcv'

@dataclass(slots=True)
class SessionCounter:
    """Stores session and session-pair replay progress."""
    
    session: int | None
    session_number: int
    symbol: str | None
    pair: int
    session_pair: int
    selected_session_pairs: int
    total_sessions: int
    total_pairs: int
    total_session_pairs: int