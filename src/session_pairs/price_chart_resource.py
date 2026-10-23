from session_pairs.resource import Resource


class PriceChartResource(Resource):
    """Provides chart slot management for price chart resources."""

    def __init__(self, chart_slot: int | None = None):
        """Initialize the resource with an optional chart slot."""
        super().__init__()
        self._validate_chart_slot(chart_slot)
        self.chart_slot = chart_slot
        self._has_explicit_chart_slot = chart_slot is not None

    def resolve_chart_slot(self, chart_slot: int):
        """Set the chart slot if one has not already been assigned."""
        self._validate_chart_slot(chart_slot)
        if self.chart_slot is None:
            self.chart_slot = chart_slot

    def inherit_chart_slot(self, chart_slot: int):
        """Set the chart slot when it was not explicitly configured."""
        self._validate_chart_slot(chart_slot)
        if not self._has_explicit_chart_slot:
            self.chart_slot = chart_slot

    @staticmethod
    def _validate_chart_slot(chart_slot: int | None):
        """Validate that the chart slot is supported."""
        if chart_slot is not None and chart_slot not in (0, 1):
            raise ValueError("chart_slot must be 0 or 1")
