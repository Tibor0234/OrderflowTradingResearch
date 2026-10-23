from collections import deque
from analyzers.news.utils import AggNewsFeatures, NewsFeatures, CachedNews

class News:
    def __init__(self, length=10, half_life_minutes=15):
        self.content: deque[CachedNews] = deque(maxlen=length)
        self.half_life_minutes = half_life_minutes

    @property
    def current(self):
        return self.content[-1]

    @property
    def aggregated(self) -> AggNewsFeatures:
        if not self.content:
            return AggNewsFeatures(
                sentiment=0.0,
                severity=0.0,
                market_relevance=0.0,
                symbol_relevance=0.0,
            )

        weights = [
            0.5 ** (-news.minutes_since_event / self.half_life_minutes)
            for news in self.content
        ]

        total_weight = sum(weights)

        if total_weight == 0:
            return AggNewsFeatures(
                sentiment=0.0,
                severity=0.0,
                market_relevance=0.0,
                symbol_relevance=0.0,
            )

        return AggNewsFeatures(
            sentiment=sum(
                news.features.sentiment * weight
                for news, weight in zip(self.content, weights)
            ) / total_weight,

            severity=sum(
                news.features.severity * weight
                for news, weight in zip(self.content, weights)
            ) / total_weight,

            market_relevance=sum(
                news.features.market_relevance * weight
                for news, weight in zip(self.content, weights)
            ) / total_weight,

            symbol_relevance=sum(
                news.features.symbol_relevance * weight
                for news, weight in zip(self.content, weights)
            ) / total_weight,
        )