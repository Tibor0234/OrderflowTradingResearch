from collections.abc import Iterable
from time import monotonic

from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from visualizers.snapshot import cache_snapshot
from trading.market_entities.increase_order import IncreaseOrder
from trading.market_entities.order import Order
from trading.market_entities.stop_order import (
    LiquidationOrder,
    StopLoss,
    StopOrder,
    TakeProfit,
)
from trading.market_entities.trade import Trade
from trading.market_entities.utils import OrderType

TRADE_PNL_UPDATE_INTERVAL_SECONDS = 0.25


class PositionVisualizer:
    """Forward snapshots of active trades and orders to the frontend."""

    def __init__(
        self,
        trades: list[Trade],
        orders: list[Order],
        increase_orders: list[IncreaseOrder],
        stop_orders: list[StopOrder],
    ):
        self.trades = trades
        self.orders = orders
        self.increase_orders = increase_orders
        self.stop_orders = stop_orders
        self._last_trade_pnl_update: dict[str, float] = {}

    def init_frontend(self) -> None:
        now = monotonic()
        for trade in self.trades:
            self._last_trade_pnl_update[str(trade.id)] = now

        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "position_init",
            self._snapshot(),
        )

    def on_update(self, updated_object: object) -> None:
        payload = self._to_payload(updated_object)
        if payload is None:
            return

        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "position_update",
            payload,
        )
        if isinstance(updated_object, Trade):
            self._last_trade_pnl_update[str(updated_object.id)] = monotonic()
        self.cache_current_snapshot()

    def on_removed(self, updated_object: object) -> None:
        payload = self._to_payload(updated_object)
        if payload is None:
            return

        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "position_remove",
            payload,
        )
        if isinstance(updated_object, Trade):
            self._last_trade_pnl_update.pop(str(updated_object.id), None)
        self.cache_current_snapshot()

    def on_clear(self) -> None:
        EventBus().emit(
            EventBusMsgType.WEBSOCKET_MESSAGE,
            "position_clear",
            {},
        )
        self._last_trade_pnl_update.clear()
        self.cache_current_snapshot()

    def update_trade_pnls(self) -> None:
        now = monotonic()
        for trade in self.trades:
            last_update = self._last_trade_pnl_update.get(str(trade.id))
            if (
                last_update is None
                or now - last_update >= TRADE_PNL_UPDATE_INTERVAL_SECONDS
            ):
                self.on_update(trade)

    def cache_current_snapshot(self) -> None:
        cache_snapshot("position_init", self._snapshot())

    def _snapshot(self) -> dict[str, object]:
        return {
            "trades": self._to_payloads(self.trades),
            "orders": self._to_payloads([*self.orders, *self.increase_orders]),
            "stop_orders": self._to_payloads(self.stop_orders),
        }

    def _to_payloads(self, entities: Iterable[object]) -> list[dict[str, object]]:
        payloads = []
        for entity in entities:
            result = self._to_payload(entity)
            if result is not None:
                payloads.append(result)
        return payloads

    @staticmethod
    def _to_payload(entity: object) -> dict[str, object] | None:
        if isinstance(entity, (Trade, Order, IncreaseOrder, StopOrder)) and entity.is_shadow:
            return None

        if isinstance(entity, Trade):
            return {
                "type": "trade",
                "id": str(entity.id),
                "side": entity.side.value,
                "margin": str(entity.margin),
                "leverage": str(entity.leverage),
                "pnl": str(entity.realized_pnl + entity.floating_pnl),
                "execution_price": str(entity.execution_price),
            }

        if isinstance(entity, IncreaseOrder):
            if entity.type is not OrderType.LIMIT:
                return None
            return {
                "type": "increase_order",
                "id": str(entity.id),
                "source_id": (
                    str(entity.source_id) if entity.source_id is not None else None
                ),
                "side": entity.side.value if entity.side is not None else None,
                "margin": str(entity.margin),
                "leverage": str(entity.leverage),
                "entry_price": str(entity.entry_price),
            }

        if isinstance(entity, Order):
            if entity.type is not OrderType.LIMIT:
                return None
            return {
                "type": "order",
                "id": str(entity.id),
                "side": entity.side.value,
                "margin": str(entity.margin),
                "leverage": str(entity.leverage),
                "entry_price": str(entity.entry_price),
            }

        if isinstance(entity, LiquidationOrder):
            order_type = "liquidation_order"
        elif isinstance(entity, TakeProfit):
            order_type = "take_profit"
        elif isinstance(entity, StopLoss):
            order_type = "stop_loss"
        else:
            return None

        return {
            "type": order_type,
            "id": str(entity.id),
            "source_id": str(entity.source_id) if entity.source_id is not None else None,
            "side": entity.side.value if entity.side is not None else None,
            "close_rate": str(entity.close_rate),
            "stop_price": str(entity.price) if entity.price is not None else None,
        }
