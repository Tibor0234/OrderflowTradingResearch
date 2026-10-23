from abc import ABC, abstractmethod

class OpenInterestManagerSubscriber(ABC):
    """Defines the interface for consumers of open interest manager updates."""

    @abstractmethod
    def process_message(self, msg):
        """Handle an open interest update."""
        pass