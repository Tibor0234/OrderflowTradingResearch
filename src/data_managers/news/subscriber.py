from abc import ABC, abstractmethod

class NewsManagerSubscriber(ABC):
    @abstractmethod
    def process_message(self, msg):
        pass