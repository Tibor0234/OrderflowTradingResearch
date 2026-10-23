from enum import Enum
from decimal import Decimal
from dataclasses import dataclass

class OHLCVPeriod(Enum):
    """Defines the supported OHLCV context periods."""

    LAST_DAY = 'last_day'
    LAST_WEEK = 'last_week'

@dataclass(slots=True)
class OHLCVCandle:
    """Represents a single OHLCV candle."""

    time: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

@dataclass(slots=True)
class OHLCVMessage:
    """Contains OHLCV candles for a specific period and timeframe."""
    
    period: OHLCVPeriod
    timeframe: str
    candles: list[OHLCVCandle]