from dataclasses import dataclass
from decimal import Decimal

@dataclass(slots=True)
class OpenInterestMessage:
    """Contains an open interest update at a specific point in time."""
    
    time: int
    open_interest: Decimal