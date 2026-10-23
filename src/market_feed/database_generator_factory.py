from psycopg import Connection


class DatabaseGeneratorFactory:
    """Creates generators for streaming market data from the database."""

    def __init__(self, conn: Connection):
        """Initialize the factory with a database connection."""
        self.conn = conn

    def instrument_metadata(self, session_pair_id):
        """Return instrument metadata for the specified session pair."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    session_pair_id,
                    symbol,
                    status,
                    base_asset,
                    quote_asset,
                    contract_type,
                    tick_size,
                    quantity_step,
                    price_precision,
                    quantity_precision,
                    min_quantity,
                    min_notional,
                    onboard_date
                FROM instrument_metadata
                WHERE session_pair_id = %s
            """, (session_pair_id,))
            return cursor.fetchone()

    def trade_generator(self, session_pair_id):
        """Stream trade data for the specified session pair."""
        cursor = self.conn.cursor(
            name=f"trade_cursor_{session_pair_id}"
        )
        cursor.itersize = 5000
        try:
            cursor.execute("""
                SELECT raw
                FROM trades
                WHERE session_pair_id = %s
                ORDER BY timestamp
            """, (session_pair_id,))
            for row in cursor:
                yield row[0]
        finally:
            cursor.close()

    def orderbook_generator(self, session_pair_id):
        """Stream order book data for the specified session pair."""
        cursor = self.conn.cursor(
            name=f"ob_cursor_{session_pair_id}"
        )
        cursor.itersize = 2000
        try:
            cursor.execute("""
                SELECT raw
                FROM orderbooks
                WHERE session_pair_id = %s
                ORDER BY timestamp
            """, (session_pair_id,))
            for row in cursor:
                yield row[0]
        finally:
            cursor.close()

    def oi_generator(self, session_pair_id):
        """Stream open interest data for the specified session pair."""
        cursor = self.conn.cursor(
            name=f"oi_cursor_{session_pair_id}"
        )
        cursor.itersize = 100
        try:
            cursor.execute("""
                SELECT raw
                FROM open_interest
                WHERE session_pair_id = %s
                ORDER BY timestamp
            """, (session_pair_id,))
            for row in cursor:
                yield row[0]
        finally:
            cursor.close()

    def ohlcv_generator(self, session_pair_id):
        """Stream OHLCV candle data grouped into fetch packages."""
        cursor = self.conn.cursor(
            name=f"ohlcv_cursor_{session_pair_id}"
        )
        try:
            cursor.execute("""
                SELECT
                    fetch_row.id,
                    fetch_row.interval,
                    fetch_row.period,
                    fetch_row.timestamp,
                    candle.open_time,
                    candle.raw
                FROM ohlcv_fetches AS fetch_row
                JOIN ohlcv AS candle
                    ON candle.fetch_id = fetch_row.id
                WHERE fetch_row.session_pair_id = %s
                ORDER BY fetch_row.timestamp, candle.open_time
            """, (session_pair_id,))

            fetches = {}
            for (
                fetch_id,
                interval,
                period,
                fetch_timestamp,
                open_time,
                raw_candle,
            ) in cursor:
                fetch = fetches.setdefault(
                    fetch_id,
                    {
                        "interval": interval,
                        "period": period,
                        "timestamp": fetch_timestamp,
                        "candles": [],
                    },
                )
                fetch["candles"].append((open_time, raw_candle))

            packages = []
            for fetch in fetches.values():
                candles = [
                    raw_candle
                    for _, raw_candle in sorted(
                        fetch["candles"],
                        key=lambda candle: candle[0],
                    )
                ]
                packages.append({
                    "period": fetch["period"],
                    "interval": fetch["interval"],
                    "open_time": int(candles[0]["open_time"]),
                    "candles": candles,
                    "fetch_timestamp": fetch["timestamp"],
                })

            for package in sorted(
                packages,
                key=lambda package: package["fetch_timestamp"]
            ):
                yield package
        finally:
            cursor.close()

    def news_generator(self, session_pair_id):
        """Stream news data for the specified session pair."""
        cursor = self.conn.cursor(
            name=f"news_cursor_{session_pair_id}"
        )
        cursor.itersize = 500
        try:
            cursor.execute("""
                SELECT external_id, timestamp, category, headline, summary
                FROM news
                WHERE session_pair_id = %s
                ORDER BY timestamp
            """, (session_pair_id,))
            for external_id, timestamp, category, headline, summary in cursor:
                yield {
                    "external_id": external_id,
                    "time": int(timestamp.timestamp() * 1000),
                    "category": category,
                    "headline": headline,
                    "summary": summary,
                }
        finally:
            cursor.close()
