from analyzers.big_trades.model import BigTrades
from global_services.data.provider import DataProvider

def get_big_trade_dominance(big_trades: BigTrades, window_seconds=None, length=None):
    """Return volume-weighted big-trade dominance in the range [-1, 1]."""
    if window_seconds is not None and window_seconds <= 0:
        raise ValueError("window_seconds must be greater than 0")

    if not big_trades.content:
        return 0.0

    window_start = None

    if window_seconds is not None:
        window_start = (
            DataProvider().get_time()
            - window_seconds * 1000
        )

    buy_volume = 0.0
    sell_volume = 0.0

    records_checked = 0

    for record in reversed(big_trades.content):
        if length is not None and records_checked >= length:
            break

        if window_start is not None and record.time < window_start:
            break

        quantity = float(record.quantity)

        if record.side.value > 0:
            buy_volume += quantity
        elif record.side.value < 0:
            sell_volume += quantity

        records_checked += 1

    total_volume = buy_volume + sell_volume

    if total_volume == 0:
        return 0.0

    return (buy_volume - sell_volume) / total_volume

def get_big_trade_intensity(big_trades: BigTrades, window_seconds=60, length=None):
    """Return the number of big trades per minute in the time window."""
    if window_seconds <= 0:
        raise ValueError("window_seconds must be greater than 0")

    if not big_trades.content:
        return 0.0

    window_start = DataProvider().get_time() - window_seconds * 1000
    records = reversed(big_trades.content)

    count = 0

    for i, record in enumerate(records):
        if length is not None and i >= length:
            break

        if record.time < window_start:
            # Ha a sequence időrendben van, innen már nem kell tovább menni.
            break

        count += 1

    return count * 60 / window_seconds