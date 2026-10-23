from abc import ABC, abstractmethod

class Resource(ABC):
    """Defines the base interface for session pair resources."""

    def __init__(self):
        """Initialize the resource model."""
        self.model: object

    @abstractmethod
    def reset(self):
        """Reset the resource to its initial state."""
        pass