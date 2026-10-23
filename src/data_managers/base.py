from abc import ABC, abstractmethod

class DataManager(ABC):
    """Defines the interface for all data managers."""

    @abstractmethod
    def forward_message(self, msg):
        """Handle an incoming message and forward it to subscribers."""
        pass