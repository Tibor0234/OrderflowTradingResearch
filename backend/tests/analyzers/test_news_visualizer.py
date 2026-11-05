from types import SimpleNamespace
from unittest.mock import Mock

from analyzers.news.analyzer import NewsAnalyzer
from analyzers.news.model import News
from analyzers.news.utils import AggNewsFeatures
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.news_panel.news_visualizer import NewsVisualizer


def test_news_visualizer_initializes_news_panel(monkeypatch):
    emitted_messages = []
    monkeypatch.setattr(
        EventBus(),
        "emit",
        lambda *args: emitted_messages.append(args),
    )
    visualizer = NewsVisualizer(News())

    visualizer.init_frontend()

    assert emitted_messages == [
        (
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "resource_init",
            {"resource_type": "news", "target": "news_panel"},
        )
    ]


def test_news_visualizer_sends_latest_news_and_aggregated_features(monkeypatch):
    emitted_messages = []
    monkeypatch.setattr(
        EventBus(),
        "emit",
        lambda *args: emitted_messages.append(args),
    )
    model = SimpleNamespace(
        current=SimpleNamespace(
            message=SimpleNamespace(time=123456, headline="Latest headline")
        ),
        aggregated=AggNewsFeatures(
            sentiment=0.25,
            severity=0.5,
            market_relevance=0.75,
            symbol_relevance=1.0,
        ),
    )
    visualizer = NewsVisualizer(model)

    visualizer.on_news()

    assert emitted_messages == [
        (
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "market_update",
            {
                "resource_type": "news",
                "target": "news_panel",
                "time": 123456,
                "headline": "Latest headline",
                "aggregated": {
                    "sentiment": 0.25,
                    "severity": 0.5,
                    "market_relevance": 0.75,
                    "symbol_relevance": 1.0,
                },
            },
        )
    ]


def test_news_analyzer_updates_visualizer_for_each_processed_message(monkeypatch):
    analyzer = NewsAnalyzer.__new__(NewsAnalyzer)
    analyzer.model = News()
    analyzer.visualizer = Mock()
    cached_news = object()
    monkeypatch.setattr(analyzer, "_extract_features", lambda message: cached_news)

    analyzer.process_message(SimpleNamespace())

    assert list(analyzer.model.content) == [cached_news]
    analyzer.visualizer.on_news.assert_called_once_with()
