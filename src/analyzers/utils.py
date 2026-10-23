from dataclasses import dataclass
from decimal import Decimal

@dataclass(slots=True)
class OscillatorRecord:
    """Stores an oscillator value at a specific point in time."""
    
    time: int
    value: Decimal

@dataclass(slots=True)
class MonotonicTrend:
    """Stores the result of a monotonic trend analysis."""

    is_trending: bool
    length: int
    direction: int

@dataclass(slots=True)
class Outlier:
    """Stores the result and relative strength of an outlier analysis."""
    
    is_outlier: bool
    strength: float