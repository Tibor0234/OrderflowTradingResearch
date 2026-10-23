from abc import ABC, abstractmethod
from decimal import Decimal

class BaseEquityCurve(ABC):
    """Provides the base logic for storing and compressing equity curve data."""

    def __init__(self, max_points=10_000):
        """Initialize the equity curve with the maximum number of stored points."""
        if max_points < 3:
            raise ValueError("max_points must be at least 3")

        self.content: dict = {}
        self._point_weights: dict = {}
        self.starting_equity: Decimal
        self.max_points = max_points

    def _add_point(self, time, equity):
        """Add an equity point and compress the curve when the limit is reached."""
        self.content[time] = equity
        self._point_weights[time] = 1

        if len(self.content) >= self.max_points:
            self._compress_content()

    def _clear_content(self):
        """Clear all stored equity points and their weights."""
        self.content.clear()
        self._point_weights.clear()

    def _compress_content(self):
        """Compress the stored equity points to reduce memory usage."""
        target_point_count = self.max_points // 2

        if len(self.content) <= target_point_count:
            return

        points = [
            (time, equity, self._point_weights.get(time, 1))
            for time, equity in self.content.items()
        ]
        sampled_points = [points[0]]
        bucket_size = (len(points) - 2) / (target_point_count - 2)

        for bucket_index in range(target_point_count - 2):
            bucket_start = int(bucket_index * bucket_size) + 1
            bucket_end = min(int((bucket_index + 1) * bucket_size) + 1, len(points) - 1)
            bucket = points[bucket_start:bucket_end]
            total_weight = sum(point[2] for point in bucket)
            average_time = sum(point[0] * point[2] for point in bucket) // total_weight
            average_equity = sum(point[1] * point[2] for point in bucket) / total_weight
            sampled_points.append((average_time, average_equity, total_weight))

        sampled_points.append(points[-1])
        self.content = {time: equity for time, equity, _ in sampled_points}
        self._point_weights = {time: weight for time, _, weight in sampled_points}

    @abstractmethod
    def is_initialized(self):
        """Return whether the equity curve has been initialized."""
        pass

    @abstractmethod
    def start_session_pair(self):
        """Initialize the equity curve for a new session pair."""
        pass

    @abstractmethod
    def update(self, equity):
        """Update the equity curve with the latest equity value."""
        pass