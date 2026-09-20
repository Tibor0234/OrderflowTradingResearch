from dataclasses import dataclass
from data_managers.news.utils import NewsMessage
from global_services.data.provider import DataProvider

@dataclass
class NewsFeatures:
    sentiment: float
    severity: float
    market_relevance: float
    symbol_relevance: float

@dataclass
class CachedNews:
    message: NewsMessage
    features: NewsFeatures

    @property
    def minutes_since_event(self) -> float:
        return (DataProvider().get_time() - self.message.time) / 1000 / 60

@dataclass
class AggNewsFeatures:
    sentiment: float
    severity: float
    market_relevance: float
    symbol_relevance: float