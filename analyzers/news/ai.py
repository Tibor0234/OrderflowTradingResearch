import json
import ollama
from data_managers.news.utils import NewsMessage
from global_services.data.provider import DataProvider

class AINewsAnalyzer:

    def __init__(self, model="qwen3:4b"):
        self.model = model

    def analyze(self, msg: NewsMessage) -> dict:
        symbol = DataProvider().get_symbol()
        prompt = f"""
        Analyze this news for the {msg.category} market and {symbol}. 

        Return ONLY valid JSON with these four numeric fields:
        sentiment, severity, market_relevance, symbol_relevance

        sentiment: expected short-term market direction caused by the news.
        -1.0 = strongly bearish
        0.0 = neutral
        1.0 = strongly bullish

        severity: importance and potential impact of the event.
        0.0 = insignificant
        1.0 = extremely significant

        market_relevance: relevance to the overall {msg.category} market.
        0.0 = irrelevant
        1.0 = highly relevant

        symbol_relevance: relevance specifically to {symbol}.
        0.0 = irrelevant
        1.0 = directly relevant

        Use the information in both the headline and summary if available. Make an actual estimate; do not default to 0 when the news indicates a positive or negative effect.

        Headline: {msg.headline}
        Summary: {msg.summary}
        """

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            format="json",
            think=False,
            options={
                "temperature": 0
            }
            ,
            keep_alive="10m"
        )

        result = json.loads(response["message"]["content"])

        required = {
            "sentiment",
            "severity",
            "market_relevance",
            "symbol_relevance",
        }

        if not required.issubset(result):
            raise ValueError(f"Invalid AI response: {result}")

        return result