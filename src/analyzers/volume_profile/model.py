from analyzers.volume_profile.utils import PriceBin, POC, ValueArea, Volume

class VolumeProfile:
    """Stores rolling volume profile data and its derived metrics."""

    def __init__(self, price_bin_count: int, value_area_pct: int, length: int):
        """Initialize the volume profile configuration and state."""
        self.price_bin_count = price_bin_count
        self.value_area_pct = value_area_pct
        self.length = length

        self.content: list[PriceBin] = []

        self.current: Volume | None = None
        self.poc: POC | None = None
        self.value_area: ValueArea | None = None