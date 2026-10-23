from data_managers.base import DataManager
from data_managers.news.subscriber import NewsManagerSubscriber
from data_managers.news.utils import NewsMessage

class NewsManager(DataManager):
    def __init__(self):
        self.subscribers: list[NewsManagerSubscriber] = []

    def subscribe(self, subscriber: NewsManagerSubscriber):
        self.subscribers.append(subscriber)
        return self

    def forward_message(self, msg):
        conv_msg = NewsMessage(
            external_id=msg["external_id"],
            time=msg["time"],
            category=msg["category"],
            headline=msg["headline"],
            summary=msg["summary"]
        )

        for sub in self.subscribers:
            sub.process_message(conv_msg)