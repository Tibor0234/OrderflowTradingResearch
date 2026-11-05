from dataclasses import asdict

from analyzers.news.model import News
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class NewsVisualizer:
    """Forwards the latest news item and aggregated features to the news panel."""

    def __init__(self, model: News):
        self.model = model

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "resource_init",
            self._init_payload(),
        )

    def on_news(self):
        latest_news = self.model.current
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "market_update",
            {
                "resource_type": "news",
                "target": "news_panel",
                "time": latest_news.message.time,
                "headline": latest_news.message.headline,
                "aggregated": asdict(self.model.aggregated),
            },
        )
        self.cache_current_snapshot()

    def cache_current_snapshot(self) -> None:
        cache_snapshot("resource_init", self._init_payload())

    def _init_payload(self) -> dict[str, object]:
        return {
            "resource_type": "news",
            "target": "news_panel",
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        return {
            "items": [
                {
                    "time": item.message.time,
                    "category": item.message.category,
                    "headline": item.message.headline,
                    "summary": item.message.summary,
                    "features": asdict(item.features),
                }
                for item in self.model.content
            ],
            "aggregated": asdict(self.model.aggregated),
        }
