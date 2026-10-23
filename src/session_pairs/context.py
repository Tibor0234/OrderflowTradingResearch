from session_pairs.resource import Resource
from session_pairs.utils import InstrumentMetadata
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType

class SessionPairContext:
    """Provides access to resources and metadata for the current session pair."""

    def __init__(self):
        """Initialize the context and subscribe to session pair events."""
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_START, self.start_new_session_pair)
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_METADATA, self.set_instrument_metadata)

        self.resources: dict[str, Resource] = {}
        self.instrument_metadata: InstrumentMetadata | None = None

    def set_resources(self, resources: dict[str, Resource]):
        """Set the resources available in the current session pair."""
        self.resources = resources
        return self

    def start_new_session_pair(self):
        """Reset all resources when a new session pair starts."""
        for resource in self.resources.values():
            resource.reset()

    def set_instrument_metadata(self, instrument_metadata=None):
        """Set the instrument metadata for the current session pair."""
        self.instrument_metadata = instrument_metadata

    def get_resource(self, name: str):
        """Return the model associated with the specified resource."""
        resource = self.resources.get(name, None)
        return resource.model if resource else None

    def get_instrument_metadata(self) -> InstrumentMetadata | None:
        """Return the instrument metadata for the current session pair."""
        return self.instrument_metadata