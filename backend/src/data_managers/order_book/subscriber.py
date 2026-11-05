from abc import ABC, abstractmethod

class OrderBookManagerSubscriber(ABC):
    """Defines the interface for consumers of order book manager updates."""

    @abstractmethod
    def process_message(self, msg):
        """Handle an order book update."""
        pass