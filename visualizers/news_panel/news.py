from analyzers.news.model import News
from visualizers.utils import colorize_number

class NewsVisualizer:
    def __init__(self, model):
        self.model: News = model

    def get_aggregated_features(self):
        categories = [
            "Sentiment",
            "Severity",
            "Mkt. Rel.",
            "Sym. Rel.",
        ]

        features = self.model.aggregated

        values = [
            colorize_number(float(features.sentiment), min_value=0),
            colorize_number(float(features.severity), min_value=0.5),
            colorize_number(float(features.market_relevance), min_value=0.5),
            colorize_number(float(features.symbol_relevance), min_value=0.5),
        ]

        return categories, values

    def get_headlines(self):
        return [news.message.headline for news in list(self.model.content)[-3:][::-1]]