from analyzers.big_trades.model import BigTrades
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot


class BigTradesVisualizer:
    """Forwards big-trade snapshots for a chart."""

    def __init__(self, model: BigTrades, chart_id: int | None, top_pct: float):
        self.model = model
        self.chart_id = chart_id
        self.top_pct = top_pct

    def init_frontend(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "resource_init",
            self._init_payload(),
        )

    def on_candle_close(self):
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "market_update",
            {
                "resource_type": "big_trades",
                "target": f"main_chart/{self.chart_id}",
                "trades": [
                    {
                        "time": trade.time,
                        "price": trade.price,
                        "quantity": trade.quantity,
                        "side": trade.side.value,
                    }
                    for trade in self.model.content
                ],
            },
        )
        self.cache_current_snapshot()

    def cache_current_snapshot(self) -> None:
        cache_snapshot("resource_init", self._init_payload())

    def _init_payload(self) -> dict[str, object]:
        return {
            "resource_type": "big_trades",
            "target": f"main_chart/{self.chart_id}",
            "top_pct": self.top_pct,
            "snapshot": self._snapshot(),
        }

    def _snapshot(self) -> dict[str, object]:
        return {
            "trades": [
                {
                    "time": trade.time,
                    "price": trade.price,
                    "quantity": trade.quantity,
                    "side": trade.side.value,
                }
                for trade in self.model.content
            ],
        }
