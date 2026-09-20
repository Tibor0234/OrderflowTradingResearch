from decimal import Decimal

class DataProvider:
    """Provides shared access to the latest market data."""

    _instance = None

    symbol: str
    price: Decimal
    time: int

    def __new__(cls):
        """Initialize the singleton instance on first access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.symbol = None
            cls._instance.price = Decimal(0)
            cls._instance.time = 0
        return cls._instance

    # setters

    def set_symbol(self, symbol: str):
        """Update the current symbol."""
        self.symbol = symbol

    def set_price(self, price: Decimal):
        """Update the current price."""
        self.price = price

    def set_time(self, time: int):
        """Update the current timestamp."""
        self.time = time

    # getters

    def get_symbol(self) -> str:
        """Retrieve the current symbol."""
        return self.symbol

    def get_price(self) -> Decimal:
        """Retrieve the current price."""
        return self.price

    def get_time(self) -> int:
        """Retrieve the current timestamp."""
        return self.time