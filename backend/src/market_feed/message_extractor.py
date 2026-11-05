class MessageExtractor:
    """Extracts timestamps and other metadata from market data messages."""

    @staticmethod
    def extract_timestamp(item):
        """Extract a timestamp from a message using its supported fields."""
        return (
            item.get("T")
            or item.get("time")
            or item.get("E")
            or item.get("open_time")
        )
