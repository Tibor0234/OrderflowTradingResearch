from market_feed.session_pair_manager import SessionPairManager


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, *_):
        pass

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return FakeCursor(self.rows)


def test_session_counter_keeps_unique_selected_symbols_in_pair_order():
    rows = [
        (1, 10, "BTCUSDT", None),
        (2, 11, "ethusdt", None),
        (3, 12, "BTCUSDT", None),
    ]

    manager = SessionPairManager(FakeConnection(rows))

    assert manager.counter.selected_symbols == ["BTCUSDT", "ETHUSDT"]
