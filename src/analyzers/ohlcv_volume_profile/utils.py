from dataclasses import dataclass
from decimal import Decimal
from analyzers.volume_profile.utils import POC, ValueArea

@dataclass(slots=True)
class OHLCVPriceBin:
    """Represents a price bin in the OHLCV volume profile."""

    low: Decimal
    size: Decimal
    volume: Decimal