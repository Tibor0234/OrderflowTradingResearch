import json

import yaml

from session_pairs.resource import Resource
from data_managers.news.subscriber import NewsManagerSubscriber
from data_managers.news.utils import NewsMessage
from analyzers.news.model import News
from analyzers.news.utils import NewsFeatures, CachedNews
from analyzers.news.db import DBNewsAnalyzer
from analyzers.news.ai import AINewsAnalyzer

class NewsAnalyzer(Resource, NewsManagerSubscriber):
    """Analyzes incoming news and maintains a rolling, time-weighted feature history."""

    def __init__(self, length=10, half_life_minutes=15, visualize=True):
        """Initialize the analyzer, loading its DB/AI dependencies from config.yaml."""
        self.model: News = News(length=length, half_life_minutes=half_life_minutes)

        with open("config.yaml", encoding="utf-8") as config_file:
            news_config = yaml.safe_load(config_file).get("news", {})

        db_path = news_config.get("db_path")
        if not db_path:
            raise ValueError("news.db_path must be set in config.yaml")

        self.db_analyzer = DBNewsAnalyzer(db_path)
        self.ai_analyzer = AINewsAnalyzer(model=news_config.get("ai_model", "qwen3:4b"))
        self.visualize = visualize

    @property
    def visualizer(self):
        """Return the news visualizer when visualization is enabled. Not implemented yet."""
        if self.visualize:
            from visualizers.news_panel.news import NewsVisualizer
            return NewsVisualizer(self.model)
        return None

    def reset(self):
        """Clear the accumulated news feature history."""
        self.model.content.clear()

    def process_message(self, msg: NewsMessage):
        """Analyze an incoming news message and append its resulting features to the model."""
        features = self._extract_features(msg)
        self.model.content.append(features)

    def _extract_features(self, msg: NewsMessage) -> CachedNews:
        """Return the DB-cached analysis if present, otherwise analyze with AI and cache the result."""
        cached = self.db_analyzer.analyze(msg)
        if cached is not None:
            result = json.loads(cached)
        else:
            result = self.ai_analyzer.analyze(msg)
            self.db_analyzer.save(msg, json.dumps(result))

        return CachedNews(
            message=msg,
            features=NewsFeatures(
                sentiment=result["sentiment"],
                severity=result["severity"],
                market_relevance=result["market_relevance"],
                symbol_relevance=result["symbol_relevance"],
            )
        )