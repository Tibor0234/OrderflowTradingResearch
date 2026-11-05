from enum import Enum
from dataclasses import dataclass, field

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
    symbol: str | None
    session_pair_count: int
    selected_session_pairs: int
    selected_symbols: list[str] = field(default_factory=list)