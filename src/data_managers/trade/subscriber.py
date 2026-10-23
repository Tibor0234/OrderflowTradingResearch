from abc import ABC, abstractmethod

class TradeManagerSubscriber(ABC):
    """Defines the interface for consumers of trade manager updates."""

    @abstractmethod
    def process_message(self, msg):
        """Handle a trade update."""
        pass
