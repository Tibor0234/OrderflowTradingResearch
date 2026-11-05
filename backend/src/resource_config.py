import inspect

from session_pairs.resource import Resource

# Resources
from analyzers.timeframe.analyzer import TimeframeAnalyzer
from analyzers.open_interest.analyzer import OpenInterestAnalyzer
from analyzers.big_trades.analyzer import BigTradesAnalyzer
from analyzers.volume_delta.simple_analyzer import VolumeDeltaAnalyzer
from analyzers.volume_delta.cumulative_analyzer import CVDAnalyzer
from analyzers.volume_profile.analyzer import VolumeProfileAnalyzer
from analyzers.ohlcv_timeframe.analyzer import OHLCVTimeframeAnalyzer, OHLCVPeriod
from analyzers.ohlcv_volume_profile.analyzer import OHLCVVolumeProfileAnalyzer
from analyzers.news.analyzer import NewsAnalyzer

# Strategies
from strategies.executable.test import TestStrategy

class ResourceConfig:
    """Configures the strategy, resources, and their dependencies."""

    def get_essentials(self):
        """Build and return the configured strategy and resources."""
        # ==================== USER CONFIG ====================
        # Select the strategy to execute.
        strategy = TestStrategy()

        resources = self._build_resources()
        self._setup_resources(resources)

        return strategy, resources

    def _build_resources(self) -> dict[str, Resource]:
        """Create the configured analyzer resources."""
        # ==================== USER CONFIG ====================
        # Declare the analyzers, their names, and their settings.
        resources = {
            "tf_1m": TimeframeAnalyzer(
                candle_seconds=60,
                length=100
            ),
            "vp_1m": VolumeProfileAnalyzer(),
        }

        return resources

    def _setup_resources(self, resources: dict[str, Resource]) -> None:
        """Subscribe resources to their compatible data sources."""
        self._assign_chart_ids(resources)
        resource_list = list(resources.values())

        for index, current in enumerate(resource_list):
            self._subscribe_to_source(current, resource_list[:index])

    def _assign_chart_ids(self, resources: dict[str, Resource]) -> None:
        """Assign independent chart IDs to main and context timeframes."""
        next_main_chart_id = 0
        next_context_chart_id = 0

        for resource in resources.values():
            if isinstance(resource, TimeframeAnalyzer):
                resource.chart_id = next_main_chart_id
                resource.setup_visualizer()
                next_main_chart_id += 1
            elif isinstance(resource, OHLCVTimeframeAnalyzer):
                resource.chart_id = next_context_chart_id
                resource.setup_visualizer()
                next_context_chart_id += 1

    def _subscribe_to_source(self, current: Resource, previous_resources: list[Resource]):
        """Subscribe a resource to the nearest compatible preceding resource."""
        for previous in reversed(previous_resources):
            if not hasattr(previous, "subscribe"):
                continue

            parameters = list(inspect.signature(previous.subscribe).parameters.values())
            expected_type = parameters[0].annotation

            if expected_type is not inspect._empty and issubclass(type(current), expected_type):
                previous.subscribe(current)
                return
