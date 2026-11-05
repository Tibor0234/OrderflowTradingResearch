from decimal import Decimal
from unittest.mock import Mock

from analyzers.utils import OscillatorRecord
from analyzers.volume_delta.model import VolumeDelta
from strategies.executable.test import TestStrategy as StrategyUnderTest
from trading.market_entities.stop_order import ReduceOnly
from trading.market_entities.utils import Side


def make_strategy(volume_delta):
    strategy = StrategyUnderTest()
    strategy.fw = Mock()
    strategy.fw.get_resource.return_value = volume_delta
    return strategy


def test_positive_one_minute_volume_delta_places_market_long():
    volume_delta = VolumeDelta(length=2)
    volume_delta.history.append(OscillatorRecord(time=60_000, value=Decimal("5")))
    strategy = make_strategy(volume_delta)
    strategy.fw.is_trade_open.return_value = False
    strategy.fw.is_order_pending.return_value = False

    strategy.on_candle_close(60)

    strategy.fw.place_market_order.assert_called_once_with(
        side=Side.BUY,
        margin=1000,
        leverage=10,
        metadata={"entry_reason": "positive 1m volume delta"},
    )
    strategy.fw.place_reduce_only_order.assert_not_called()


def test_negative_one_minute_volume_delta_closes_open_trades():
    volume_delta = VolumeDelta(length=2)
    volume_delta.history.append(OscillatorRecord(time=60_000, value=Decimal("-5")))
    strategy = make_strategy(volume_delta)
    trade = Mock()
    strategy.fw.get_trades.return_value = [trade]
    strategy.fw.get_stop_orders.return_value = []

    strategy.on_candle_close(60)

    strategy.fw.place_reduce_only_order.assert_called_once_with(
        source=trade,
        pct=100,
        metadata={"exit_reason": "negative 1m volume delta"},
    )
    strategy.fw.place_market_order.assert_not_called()


def test_negative_volume_delta_does_not_duplicate_pending_exit():
    volume_delta = VolumeDelta(length=2)
    volume_delta.history.append(OscillatorRecord(time=60_000, value=Decimal("-5")))
    strategy = make_strategy(volume_delta)
    trade = Mock()
    strategy.fw.get_trades.return_value = [trade]
    strategy.fw.get_stop_orders.return_value = [ReduceOnly(pct=100)]

    strategy.on_candle_close(60)

    strategy.fw.place_reduce_only_order.assert_not_called()


def test_strategy_ignores_non_minute_closes_and_zero_volume_delta():
    volume_delta = VolumeDelta(length=2)
    volume_delta.history.append(OscillatorRecord(time=60_000, value=Decimal("0")))
    strategy = make_strategy(volume_delta)
    strategy.fw.is_trade_open.return_value = False
    strategy.fw.is_order_pending.return_value = False

    strategy.on_candle_close(300)
    strategy.on_candle_close(60)

    strategy.fw.place_market_order.assert_not_called()
    strategy.fw.place_reduce_only_order.assert_not_called()
