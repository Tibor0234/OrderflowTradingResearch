from decimal import Decimal
from unittest.mock import Mock

import pytest

from strategies.core.framework import StrategyFramework
from trading.market_entities.stop_order import StopLoss


def test_stop_loss_close_rate_is_configurable_through_strategy_framework():
    position_manager = Mock()
    source = Mock()
    framework = StrategyFramework(position_manager, Mock(), Mock())

    order = framework.place_stop_loss(
        source,
        Decimal("90"),
        close_rate=0.25,
    )

    assert isinstance(order, StopLoss)
    assert order.close_rate == Decimal("0.25")
    source.link.assert_called_once_with(order)
    position_manager.place_order.assert_called_once_with(order)


def test_stop_loss_requires_close_rate():
    with pytest.raises(TypeError):
        StopLoss(price=Decimal("90"))

    framework = StrategyFramework(Mock(), Mock(), Mock())
    with pytest.raises(TypeError):
        framework.place_stop_loss(Mock(), Decimal("90"))


def test_stop_loss_can_explicitly_close_the_full_position():
    order = StopLoss(price=Decimal("90"), close_rate=1.0)

    assert order.close_rate == Decimal("1.0")
