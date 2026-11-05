from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import visualizers.position_panel.position_visualizer as position_visualizer_module
from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from trading.execution.data_analysis_handler import DataAnalysisHandler
from trading.execution.position_manager import PositionManager
from trading.market_entities.increase_order import IncreaseLimitOrder
from trading.market_entities.order import LimitOrder, MarketOrder
from trading.market_entities.stop_order import (
    LiquidationOrder,
    ReduceOnlyMarket,
    StopLoss,
    TakeProfit,
)
from trading.market_entities.trade import Trade
from trading.market_entities.utils import OrderType, Side
from visualizers.position_panel.position_visualizer import PositionVisualizer


def test_position_visualizer_sends_snapshot_and_minimal_order_update():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order = LimitOrder(
        side=Side.BUY,
        margin=Decimal("100"),
        entry_price=Decimal("98"),
        leverage=2,
    )
    visualizer = PositionVisualizer([], [order], [], [])

    try:
        visualizer.init_frontend()
        visualizer.on_update(order)
        visualizer.on_removed(order)

        assert messages == [
            (
                "position_init",
                {
                    "trades": [],
                    "orders": [
                        {
                            "type": "order",
                            "id": str(order.id),
                            "side": Side.BUY.value,
                            "margin": "100",
                            "leverage": "2",
                            "entry_price": "98",
                        }
                    ],
                    "stop_orders": [],
                },
            ),
            (
                "position_update",
                {
                    "type": "order",
                    "id": str(order.id),
                    "side": Side.BUY.value,
                    "margin": "100",
                    "leverage": "2",
                    "entry_price": "98",
                },
            ),
            (
                "position_remove",
                {
                    "type": "order",
                    "id": str(order.id),
                    "side": Side.BUY.value,
                    "margin": "100",
                    "leverage": "2",
                    "entry_price": "98",
                },
            ),
        ]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_position_visualizer_does_not_send_shadow_positions():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)

    shadow_trade = Trade(
        id=uuid4(),
        execution_price=Decimal("100"),
        side=Side.BUY,
        margin=Decimal("10"),
        leverage=1,
        is_shadow=True,
    )
    shadow_order = LimitOrder(
        side=Side.BUY,
        margin=Decimal("20"),
        entry_price=Decimal("95"),
        is_shadow=True,
    )
    shadow_increase_order = IncreaseLimitOrder(
        margin=Decimal("30"),
        entry_price=Decimal("90"),
    )
    shadow_increase_order.is_shadow = True
    shadow_stop_order = TakeProfit(
        price=Decimal("120"),
        type=OrderType.LIMIT,
        close_rate=1.0,
    )
    shadow_stop_order.is_shadow = True
    shadow_positions = [
        shadow_trade,
        shadow_order,
        shadow_increase_order,
        shadow_stop_order,
    ]
    visualizer = PositionVisualizer(
        [shadow_trade],
        [shadow_order],
        [shadow_increase_order],
        [shadow_stop_order],
    )

    try:
        visualizer.init_frontend()
        for position in shadow_positions:
            visualizer.on_update(position)
            visualizer.on_removed(position)

        assert messages == [
            (
                "position_init",
                {"trades": [], "orders": [], "stop_orders": []},
            )
        ]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_position_manager_updates_frontend_for_fill_and_trade_close():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order_book = Mock()
    order_book.calculate_market_fill.side_effect = [
        Decimal("100"),
        Decimal("101"),
    ]
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=order_book,
        order_flow=Mock(),
        data_analysis_handler=DataAnalysisHandler(),
    )
    order = MarketOrder(
        side=Side.BUY,
        margin=Decimal("100"),
        leverage=1,
    )
    DataProvider().set_time(1)
    DataProvider().set_price(Decimal("100"))

    try:
        assert position_manager.position_visualizer.trades is position_manager.trades
        assert position_manager.position_visualizer.orders is position_manager.orders
        assert (
            position_manager.position_visualizer.stop_orders
            is position_manager.stop_orders
        )

        position_manager.place_order(order)
        position_manager.on_order_triggered(order)
        position_manager.on_stop_order_triggered(position_manager.stop_orders[0])

        position_messages = [
            (message_type, data)
            for message_type, data in messages
            if message_type in {"position_update", "position_remove"}
        ]
        assert [message_type for message_type, _ in position_messages] == [
            "position_update",
            "position_update",
            "position_remove",
            "position_remove",
        ]
        assert set(position_messages[0][1]) == {
            "type",
            "id",
            "side",
            "margin",
            "leverage",
            "pnl",
            "execution_price",
        }
        assert position_messages[0][1]["id"] == str(order.id)
        assert position_messages[1][1]["type"] == "liquidation_order"
        assert position_messages[2][1]["type"] == "liquidation_order"
        assert position_messages[2][1]["source_id"] == str(order.id)
        assert position_messages[3][1]["id"] == str(order.id)
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_position_manager_does_not_update_frontend_when_order_does_not_fill():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order_flow = Mock()
    order_flow.calculate_limit_fill.return_value = (Decimal("100"), Decimal(0))
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=order_flow,
        data_analysis_handler=DataAnalysisHandler(),
    )
    order = LimitOrder(
        side=Side.BUY,
        margin=Decimal("100"),
        entry_price=Decimal("100"),
    )

    try:
        position_manager.on_order_triggered(order)
        assert messages == []
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_position_manager_emits_removed_for_cancelled_limit_order():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=Mock(),
        data_analysis_handler=DataAnalysisHandler(),
    )
    order = LimitOrder(
        side=Side.SELL,
        margin=Decimal("50"),
        entry_price=Decimal("105"),
    )

    try:
        position_manager.place_order(order)
        assert messages == [
            (
                "position_update",
                {
                    "type": "order",
                    "id": str(order.id),
                    "side": Side.SELL.value,
                    "margin": "50",
                    "leverage": "1",
                    "entry_price": "105",
                },
            )
        ]
        messages.clear()

        position_manager.cancel_order(order)

        assert messages == [
            (
                "position_remove",
                {
                    "type": "order",
                    "id": str(order.id),
                    "side": Side.SELL.value,
                    "margin": "50",
                    "leverage": "1",
                    "entry_price": "105",
                },
            )
        ]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_partial_limit_fill_removes_order_and_updates_trade_replacement_and_liquidation():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order_flow = Mock()
    order_flow.calculate_limit_fill.return_value = (
        Decimal("100"),
        Decimal("40"),
    )
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=order_flow,
        data_analysis_handler=DataAnalysisHandler(),
    )
    order = LimitOrder(
        side=Side.BUY,
        margin=Decimal("100"),
        entry_price=Decimal("100"),
    )
    DataProvider().set_time(1)

    try:
        position_manager.place_order(order)
        messages.clear()

        position_manager.on_order_triggered(order)

        assert [message_type for message_type, _ in messages] == [
            "position_remove",
            "position_update",
            "position_update",
            "position_update",
        ]
        assert messages[0][1]["type"] == "order"
        assert messages[0][1]["id"] == str(order.id)
        assert set(messages[1][1]) == {
            "type",
            "id",
            "side",
            "margin",
            "leverage",
            "pnl",
            "execution_price",
        }
        assert messages[2][1]["type"] == "increase_order"
        assert messages[2][1]["margin"] == "60"
        assert messages[2][1]["source_id"] == str(position_manager.trades[0].id)
        assert messages[3][1]["type"] == "liquidation_order"
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_fully_filled_limit_order_is_removed_and_opens_trade():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order_flow = Mock()
    order_flow.calculate_limit_fill.return_value = (
        Decimal("100"),
        Decimal("100"),
    )
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=order_flow,
        data_analysis_handler=DataAnalysisHandler(),
    )
    order = LimitOrder(
        side=Side.BUY,
        margin=Decimal("100"),
        entry_price=Decimal("100"),
    )
    DataProvider().set_time(1)

    try:
        position_manager.place_order(order)
        messages.clear()

        position_manager.on_order_triggered(order)

        assert [message_type for message_type, _ in messages] == [
            "position_remove",
            "position_update",
            "position_update",
        ]
        assert messages[0][1]["type"] == "order"
        assert messages[0][1]["id"] == str(order.id)
        assert messages[1][1]["id"] == str(order.id)
        assert messages[2][1]["type"] == "liquidation_order"
        assert position_manager.orders == []
        assert position_manager.increase_orders == []
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_increase_order_partial_fill_updates_trade_order_and_liquidation():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order_flow = Mock()
    order_flow.calculate_limit_fill.return_value = (
        Decimal("95"),
        Decimal("20"),
    )
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=order_flow,
        data_analysis_handler=DataAnalysisHandler(),
    )
    trade = Trade(
        id=uuid4(),
        execution_price=Decimal("100"),
        side=Side.BUY,
        margin=Decimal("100"),
        leverage=1,
    )
    increase_order = IncreaseLimitOrder(
        margin=Decimal("50"),
        entry_price=Decimal("95"),
    )
    liquidation = LiquidationOrder(Decimal("90"))
    trade.link_many([increase_order, liquidation])
    position_manager.trades.append(trade)
    position_manager.increase_orders.append(increase_order)
    position_manager.stop_orders.append(liquidation)

    try:
        position_manager.on_order_triggered(increase_order)

        assert [message_type for message_type, _ in messages] == [
            "position_update",
            "position_update",
            "position_update",
        ]
        assert messages[0][1]["id"] == str(trade.id)
        assert messages[1][1]["type"] == "increase_order"
        assert messages[1][1]["margin"] == "30"
        assert messages[2][1]["type"] == "liquidation_order"
        assert increase_order in position_manager.increase_orders
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_fully_filled_increase_order_is_removed_and_updates_trade():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order_flow = Mock()
    order_flow.calculate_limit_fill.return_value = (
        Decimal("95"),
        Decimal("50"),
    )
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=order_flow,
        data_analysis_handler=DataAnalysisHandler(),
    )
    trade = Trade(
        id=uuid4(),
        execution_price=Decimal("100"),
        side=Side.BUY,
        margin=Decimal("100"),
        leverage=1,
    )
    increase_order = IncreaseLimitOrder(
        margin=Decimal("50"),
        entry_price=Decimal("95"),
    )
    liquidation = LiquidationOrder(Decimal("90"))
    trade.link_many([increase_order, liquidation])
    position_manager.trades.append(trade)
    position_manager.increase_orders.append(increase_order)
    position_manager.stop_orders.append(liquidation)

    try:
        position_manager.on_order_triggered(increase_order)

        assert [message_type for message_type, _ in messages] == [
            "position_remove",
            "position_update",
            "position_update",
        ]
        assert messages[0][1]["type"] == "increase_order"
        assert messages[0][1]["id"] == str(increase_order.id)
        assert messages[1][1]["id"] == str(trade.id)
        assert messages[2][1]["type"] == "liquidation_order"
        assert position_manager.increase_orders == []
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_partial_stop_fill_updates_trade_and_remaining_stop_order():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order_flow = Mock()
    order_flow.calculate_limit_fill.return_value = (
        Decimal("95"),
        Decimal("250"),
    )
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=order_flow,
        data_analysis_handler=DataAnalysisHandler(),
    )
    trade = Trade(
        id=uuid4(),
        execution_price=Decimal("100"),
        side=Side.BUY,
        margin=Decimal("1000"),
        leverage=1,
    )
    take_profit = TakeProfit(
        price=Decimal("95"),
        type=OrderType.LIMIT,
        close_rate=0.5,
    )
    trade.link(take_profit)
    position_manager.trades.append(trade)
    position_manager.stop_orders.append(take_profit)

    try:
        position_manager.on_stop_order_triggered(take_profit)

        assert [message_type for message_type, _ in messages] == [
            "position_update",
            "position_update",
        ]
        assert messages[0][1]["id"] == str(trade.id)
        assert messages[1][1]["type"] == "take_profit"
        assert messages[1][1]["close_rate"] == "0.5"
        assert take_profit in position_manager.stop_orders
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_fully_filled_take_profit_is_removed_and_updates_open_trade():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    order_flow = Mock()
    order_flow.calculate_limit_fill.return_value = (
        Decimal("95"),
        Decimal("500"),
    )
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=order_flow,
        data_analysis_handler=DataAnalysisHandler(),
    )
    trade = Trade(
        id=uuid4(),
        execution_price=Decimal("100"),
        side=Side.BUY,
        margin=Decimal("1000"),
        leverage=1,
    )
    take_profit = TakeProfit(
        price=Decimal("95"),
        type=OrderType.LIMIT,
        close_rate=0.5,
    )
    trade.link(take_profit)
    position_manager.trades.append(trade)
    position_manager.stop_orders.append(take_profit)

    try:
        position_manager.on_stop_order_triggered(take_profit)

        assert [message_type for message_type, _ in messages] == [
            "position_remove",
            "position_update",
        ]
        assert messages[0][1]["type"] == "take_profit"
        assert messages[0][1]["id"] == str(take_profit.id)
        assert messages[1][1]["id"] == str(trade.id)
        assert trade in position_manager.trades
        assert take_profit not in position_manager.stop_orders
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_place_and_cancel_increase_and_stop_orders_update_then_remove():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=Mock(),
        data_analysis_handler=DataAnalysisHandler(),
    )
    increase_order = IncreaseLimitOrder(
        margin=Decimal("50"),
        entry_price=Decimal("95"),
    )
    increase_order.set_from_source(uuid4(), Side.BUY, False)
    take_profit = TakeProfit(
        price=Decimal("110"),
        type=OrderType.LIMIT,
        close_rate=0.25,
    )
    take_profit.set_from_source(uuid4(), Side.BUY, False)

    try:
        for order, expected_type in (
            (increase_order, "increase_order"),
            (take_profit, "take_profit"),
        ):
            position_manager.place_order(order)
            assert messages[-1][0] == "position_update"
            assert messages[-1][1]["type"] == expected_type
            messages.clear()

            position_manager.cancel_order(order)
            assert messages[-1][0] == "position_remove"
            assert messages[-1][1]["type"] == expected_type
            messages.clear()
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_position_clear_is_emitted_and_registered_for_session_and_process_lifecycle():
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    position_manager = PositionManager(
        starting_balance=10000,
        order_book=Mock(),
        order_flow=Mock(),
        data_analysis_handler=DataAnalysisHandler(),
    )

    try:
        assert position_manager.on_session_pair_start in event_bus.listeners[
            EventBusMsgType.SESSION_PAIR_START
        ]
        assert position_manager.clear_state in event_bus.listeners[
            EventBusMsgType.PROCESS_END
        ]

        position_manager.on_session_pair_start()
        assert messages[-1] == ("position_clear", {})
        messages.clear()

        position_manager.clear_state()
        assert messages == [("position_clear", {})]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)


def test_position_visualizer_uses_compact_trade_and_order_shapes():
    DataProvider().set_price(Decimal("110"))
    trade = Trade(
        id=uuid4(),
        execution_price=Decimal("100"),
        side=Side.BUY,
        margin=Decimal("10"),
        leverage=1,
        metadata={},
    )
    trade.realized_pnl = Decimal("5")
    normal_order = LimitOrder(
        side=Side.BUY,
        margin=Decimal("20"),
        entry_price=Decimal("95"),
    )
    increase_order = IncreaseLimitOrder(
        margin=Decimal("30"),
        entry_price=Decimal("90"),
    )
    increase_order.set_from_source(trade.id, Side.BUY, False)
    market_order = MarketOrder(
        side=Side.SELL,
        margin=Decimal("40"),
        leverage=1,
    )
    take_profit = TakeProfit(
        price=Decimal("120"),
        type=OrderType.LIMIT,
        close_rate=0.25,
    )
    stop_loss = StopLoss(price=Decimal("80"), close_rate=1.0)
    liquidation = LiquidationOrder(price=Decimal("70"))
    for stop_order in (take_profit, stop_loss, liquidation):
        stop_order.set_from_source(trade.id, Side.BUY, False)
    reduce_only = ReduceOnlyMarket(close_rate=1.0)

    snapshot = PositionVisualizer(
        [trade],
        [normal_order, market_order],
        [increase_order],
        [take_profit, stop_loss, liquidation, reduce_only],
    )._snapshot()

    assert snapshot["trades"] == [
        {
            "type": "trade",
            "id": str(trade.id),
            "side": Side.BUY.value,
            "margin": "10",
            "leverage": "1",
            "pnl": "6",
            "execution_price": "100",
        }
    ]
    assert snapshot["orders"] == [
        {
            "type": "order",
            "id": str(normal_order.id),
            "side": Side.BUY.value,
            "margin": "20",
            "leverage": "1",
            "entry_price": "95",
        },
        {
            "type": "increase_order",
            "id": str(increase_order.id),
            "source_id": str(trade.id),
            "side": Side.BUY.value,
            "margin": "30",
            "leverage": "1",
            "entry_price": "90",
        },
    ]
    assert snapshot["stop_orders"] == [
        {
            "type": "take_profit",
            "id": str(take_profit.id),
            "source_id": str(trade.id),
            "side": Side.SELL.value,
            "close_rate": "0.25",
            "stop_price": "120",
        },
        {
            "type": "stop_loss",
            "id": str(stop_loss.id),
            "source_id": str(trade.id),
            "side": Side.SELL.value,
            "close_rate": "1",
            "stop_price": "80",
        },
        {
            "type": "liquidation_order",
            "id": str(liquidation.id),
            "source_id": str(trade.id),
            "side": Side.SELL.value,
            "close_rate": "1",
            "stop_price": "70",
        },
    ]


def test_position_visualizer_refreshes_trade_pnl_every_250ms(monkeypatch):
    messages = []
    handler = lambda *args: messages.append(args)
    event_bus = EventBus()
    event_bus.subscribe(EventBusMsgType.WEBSOCKET_MESSAGE, handler)
    now = [1.0]
    monkeypatch.setattr(position_visualizer_module, "monotonic", lambda: now[0])

    DataProvider().set_price(Decimal("100"))
    trade = Trade(
        id=uuid4(),
        execution_price=Decimal("100"),
        side=Side.BUY,
        margin=Decimal("10"),
        leverage=1,
        metadata={},
    )
    visualizer = PositionVisualizer([trade], [], [], [])

    try:
        visualizer.on_update(trade)
        messages.clear()
        DataProvider().set_price(Decimal("110"))

        now[0] += 0.249
        visualizer.update_trade_pnls()
        assert messages == []

        now[0] += 0.001
        visualizer.update_trade_pnls()

        assert messages == [
            (
                "position_update",
                {
                    "type": "trade",
                    "id": str(trade.id),
                    "side": Side.BUY.value,
                    "margin": "10",
                    "leverage": "1",
                    "pnl": "1",
                    "execution_price": "100",
                },
            )
        ]
    finally:
        event_bus.listeners[EventBusMsgType.WEBSOCKET_MESSAGE].remove(handler)
