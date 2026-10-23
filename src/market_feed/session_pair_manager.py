from psycopg import Connection

from market_feed.utils import SessionCounter


class SessionPairManager:
    """Manages session pairs and tracks replay progress."""

    def __init__(
        self,
        conn: Connection,
        session_numbers: list[int | str] | None = None,
        symbols: list[str] | None = None,
    ):
        """Initialize the manager and load the selected session pairs."""
        self.conn = conn
        self.session_numbers = self._parse_session_numbers(
            [] if session_numbers is None else session_numbers
        )
        self.symbols = self._parse_symbols([] if symbols is None else symbols)
        self._validate_symbols()
        self.session_pairs = self._load_session_pairs()
        self.all_session_pair_counts = self._load_all_session_pair_counts()
        self.counter = SessionCounter(
            session=None,
            session_number=0,
            symbol=None,
            pair=0,
            session_pair=0,
            selected_session_pairs=len(self.session_pairs),
            total_sessions=len(self.all_session_pair_counts),
            total_pairs=0,
            total_session_pairs=sum(self.all_session_pair_counts.values()),
        )

    def _load_session_pairs(self):
        """Load the selected session pairs in chronological order."""
        filters = []
        parameters = []

        if self.session_numbers:
            filters.append("s.id = ANY(%s)")
            parameters.append(self.session_numbers)

        if self.symbols:
            filters.append("UPPER(sp.pair) = ANY(%s)")
            parameters.append(self.symbols)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        with self.conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    sp.id,
                    sp.session_id,
                    sp.pair,
                    s.created_at
                FROM session_pairs sp
                JOIN sessions s
                    ON s.id = sp.session_id
                {where_clause}
                ORDER BY
                    s.created_at,
                    sp.id
            """, parameters)
            return cursor.fetchall()

    def _validate_symbols(self):
        """Validate that all requested symbols exist in the database."""
        if not self.symbols:
            return

        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT UPPER(pair)
                FROM session_pairs
                WHERE UPPER(pair) = ANY(%s)
            """, (self.symbols,))
            available_symbols = {row[0] for row in cursor.fetchall()}

        unknown_symbols = sorted(set(self.symbols) - available_symbols)
        if unknown_symbols:
            raise ValueError(
                f"Unknown symbol(s): {', '.join(unknown_symbols)}"
            )

    def _load_all_session_pair_counts(self) -> dict[int, int]:
        """Load the total number of session pairs for each session."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    session_id,
                    COUNT(*)
                FROM session_pairs
                GROUP BY session_id
            """)
            return dict(cursor.fetchall())

    @staticmethod
    def _parse_session_numbers(values: list[int | str]) -> list[int]:
        """Parse and validate session numbers and ranges."""
        if not isinstance(values, list):
            raise ValueError("sessions_numbers must be a list")

        session_numbers = set()

        for value in values:
            if isinstance(value, bool):
                raise ValueError(f"Invalid session number: {value!r}")

            if isinstance(value, int):
                if value < 1:
                    raise ValueError(f"Invalid session number: {value!r}")
                session_numbers.add(value)
                continue

            if not isinstance(value, str):
                raise ValueError(f"Invalid session number: {value!r}")

            parts = [part.strip() for part in value.split("-")]
            if len(parts) != 2 or not all(part.isdecimal() for part in parts):
                raise ValueError(f"Invalid session range: {value!r}")

            start, end = map(int, parts)
            if start < 1 or end < 1 or start > end:
                raise ValueError(f"Invalid session range: {value!r}")

            session_numbers.update(range(start, end + 1))

        return sorted(session_numbers)

    @staticmethod
    def _parse_symbols(values: list[str]) -> list[str]:
        """Normalize and validate the requested symbols."""
        if not isinstance(values, list):
            raise ValueError("symbols must be a list")

        symbols = set()

        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid symbol: {value!r}")
            symbols.add(value.strip().upper())

        return sorted(symbols)

    def get_next(self):
        """Return the next session pair and update the replay progress."""
        if self.counter.session_pair >= len(self.session_pairs):
            return None

        session_pair = self.session_pairs[self.counter.session_pair]
        _, session_id, symbol, _ = session_pair

        self.counter.pair = self.counter.pair + 1 if self.counter.session == session_id else 1
        if self.counter.session != session_id:
            self.counter.session_number += 1
        self.counter.session = session_id
        self.counter.symbol = symbol.upper()
        self.counter.total_pairs = self.all_session_pair_counts[session_id]
        self.counter.session_pair += 1
        return session_pair

    def has_next(self):
        """Return whether another session pair is available."""
        return self.counter.session_pair < len(self.session_pairs)

    def get_counter(self):
        """Return the current session counter."""
        return self.counter
