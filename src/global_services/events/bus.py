class EventBus:
    """Provides a shared event system for subscribing handlers and emitting events."""

    _instance = None

    listeners: dict

    def __new__(cls):
        """Initialize the singleton instance on first access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.listeners = {}
        return cls._instance

    def subscribe(self, event_type, handler):
        """Subscribe a handler method to an event."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(handler)

    def emit(self, event_type, *args, **kwargs):
        """Invoke all subscribed handlers with arbitrary parameters."""
        for handler in self.listeners.get(event_type, []):
            handler(*args, **kwargs)