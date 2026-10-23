import json
import ollama
from data_managers.news.utils import NewsMessage
from global_services.data.provider import DataProvider

class AINewsAnalyzer:

    def __init__(self, model="qwen3:4b"):
        self.model = model

    def analyze(self, msg: NewsMessage) -> dict:
        symbol = DataProvider().get_symbol()

        system_prompt = """
        Analyze cryptocurrency news numerically.

        Return ONLY valid JSON with these four numeric fields:
        sentiment, severity, market_relevance, symbol_relevance

        All values must follow these scales.

        sentiment:
        Expected short-term market direction caused by the specific news.
        -1.0 = strongly bearish
        -0.5 = moderately bearish
        0.0 = neutral / no clear directional effect
        +0.5 = moderately bullish
        +1.0 = strongly bullish

        severity:
        How significant the underlying EVENT is, regardless of whether it is bullish or bearish.
        0.0 = trivial / no meaningful market impact
        0.25 = minor event
        0.5 = moderately important event
        0.75 = major event
        1.0 = exceptional event with potentially large market-wide consequences

        Do NOT give high severity simply because the article is about cryptocurrency.

        market_relevance:
        How relevant this specific news is to the overall cryptocurrency market.
        0.0 = unrelated to crypto markets
        0.25 = weak connection to crypto
        0.5 = relevant to a part of the crypto market
        0.75 = relevant to a large part of the crypto market
        1.0 = directly affects the entire crypto market or is a major macro event affecting crypto

        symbol_relevance:
        How directly this news affects the analyzed symbol.
        0.0 = no meaningful connection to the symbol
        0.25 = weak or indirect connection
        0.5 = potentially affects the symbol, but not directly
        0.75 = directly related to the symbol
        1.0 = specifically about the symbol or directly affects its price, network, issuer, or market

        Do not default to high values.
        Most ordinary news should NOT receive 1.0.
        Use 1.0 only when the definition clearly justifies it.
        Distinguish carefully between market relevance and symbol relevance.
        """

        user_prompt = f"""
        Analyze this news for the {msg.category} market and {symbol}.

        Headline: {msg.headline}

        Summary: {msg.summary}
        """

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            format={
                "type": "object",
                "properties": {
                    "sentiment": {"type": "number"},
                    "severity": {"type": "number"},
                    "market_relevance": {"type": "number"},
                    "symbol_relevance": {"type": "number"}
                },
                "required": [
                    "sentiment",
                    "severity",
                    "market_relevance",
                    "symbol_relevance"
                ]
            },
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