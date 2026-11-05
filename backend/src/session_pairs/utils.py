from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class InstrumentMetadata:
    """Stores instrument metadata and trading constraints for a session pair."""
    
    session_pair_id: int
    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    contract_type: str
    tick_size: Decimal
    quantity_step: Decimal | None
    price_precision: int | None
    quantity_precision: int | None
    min_quantity: Decimal | None
    min_notional: Decimal | None
    onboard_date: datetime | None