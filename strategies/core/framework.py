from datetime import datetime
from decimal import Decimal
from typing import TypeVar
from session_pairs.context import SessionPairContext
from trading.market_entities.trade import Trade
from trading.execution.position_manager import PositionManager
from trading.market_entities.order import Order, MarketOrder, LimitOrder
from trading.market_entities.stop_order import StopOrder, TakeProfit, StopLoss, ReduceOnly
from trading.market_entities.increase_order import IncreaseOrder, IncreaseLimitOrder, IncreaseMarketOrder
from strategies.core.sequence_analyzers import SequenceAnalyzers
from trading.execution.order_book import ExecutionOrderBook
from trading.market_entities.utils import OrderType, Side
from global_services.data.provider import DataProvider
from analyzers.ohlcv_timeframe.model import OHLCVTimeframe
from analyzers.ohlcv_volume_profile.model import OHLCVVolumeProfile
from analyzers.microprice_deviation.model import MicropriceDeviation
from analyzers.open_interest.model import OpenInterest
from analyzers.order_book_imbalance.model import OrderBookImbalance
from analyzers.timeframe.model import Timeframe
from analyzers.volume_delta.model import VolumeDelta
from analyzers.volume_profile.model import VolumeProfile
from analyzers.big_trades.model import BigTrades


ModelT = TypeVar("ModelT")


class StrategyFramework(SequenceAnalyzers):
    """Provides strategies with access to trading operations, market data, and analysis resources."""

    def __init__(self, position_manager: PositionManager, session_pair_context: SessionPairContext, execution_order_book: ExecutionOrderBook):
        """Initialize the framework with position management, session context, and order book access."""
        self.position_manager = position_manager
        self.session_pair_context = session_pair_context
        self.order_book = execution_order_book

        self.orders = position_manager.orders
        self.trades = position_manager.trades

    # place orders

    def place_limit_order(self, side, value, entry_price, leverage, kill=None, kill_after_fill=None, metadata=None, is_shadow=False):
        """Create and place a limit order."""
        order = LimitOrder(
            side=Side(side),
            value=value,
            entry_price=entry_price,
            leverage=leverage,
            kill=kill * 1000 if kill is not None else None,
            kill_after_fill=kill_after_fill * 1000 if kill_after_fill is not None else None,
            metadata=metadata,
            is_shadow=is_shadow,
        )
        self.position_manager.place_order(order)
        return order
    
    def place_market_order(self, side, value, leverage, metadata=None, is_shadow=False):
        """Create and place a market order."""
        order = MarketOrder(
            side=Side(side),
            value=value,
            leverage=leverage,
            metadata=metadata,
            is_shadow=is_shadow,
        )
        self.position_manager.place_order(order)
        return order
    
    def place_increase_limit_order(self, source: Order | Trade, value, entry_price, leverage, kill_after_fill=None, metadata=None):
        """Create and place an increase limit order."""
        order = IncreaseLimitOrder(
            value=value,
            entry_price=entry_price,
            leverage=leverage,
            kill_after_fill=kill_after_fill * 1000 if kill_after_fill is not None else None,
            metadata=metadata
        )
        source.link(order)
        self.position_manager.place_order(order)
        return order
    
    def place_increase_marker_order(self, source: Order | Trade, value, leverage, metadata=None):
        """Create and place an increase market order."""
        order = IncreaseMarketOrder(
            value=value,
            leverage=leverage,
            metadata=metadata
        )
        source.link(order)
        self.position_manager.place_order(order)
        return order
    
    def place_take_profit_limit(self, source: Order | Trade, price, pct, metadata=None):
        """Create and place a take profit limit order."""
        order = TakeProfit(
            price=price,
            type=OrderType.LIMIT,
            pct=pct,
            metadata=metadata
        )
        source.link(order)
        self.position_manager.place_order(order)
        return order
    
    def place_take_profit_market(self, source: Order | Trade, price, pct, metadata=None):
        """Create and place a take profit market order."""
        order = TakeProfit(
            price=price,
            type=OrderType.MARKET,
            pct=pct,
            metadata=metadata
        )
        source.link(order)
        self.position_manager.place_order(order)
        return order
    
    def place_stop_loss(self, source: Order | Trade, price, metadata=None):
        """Create and place a stop loss order."""
        order = StopLoss(
            price=price,
            metadata=metadata
        )
        source.link(order)
        self.position_manager.place_order(order)
        return order
    
    def place_reduce_only_order(self, source: Order | Trade, pct, metadata=None):
        """Create and place a reduce only order."""
        order = ReduceOnly(
            pct=pct,
            metadata=metadata
        )
        source.link(order)
        self.position_manager.place_order(order)
        return order

    # position manager actions

    def cancel_order(self, order: Order | IncreaseOrder | StopOrder):
        """Cancel an existing order."""
        self.position_manager.cancel_order(order)

    def trail_stop_loss(self, trade: Trade, price):
        """Trail the stop loss for an open trade."""
        sl = self.get_next_stop_loss(trade)
        if sl: 
            sl.price = Decimal(price)
        else:
            sl_order = StopLoss(Decimal(price))
            trade.link(sl_order)
            self.position_manager.place_order(sl_order)
    
    # execution queries

    def is_trade_open(self):
        """Return whether an active non-shadow trade exists."""
        return any(not trade.is_shadow for trade in self.position_manager.trades)

    def is_order_pending(self):
        """Return whether there are any pending non-shadow orders."""
        return any(not order.is_shadow for order in self.position_manager.orders + self.position_manager.increase_orders)

    def get_trades(self):
        """Return a copy of the active non-shadow trades."""
        return [trade for trade in self.position_manager.trades if not trade.is_shadow]

    def get_orders(self):
        """Return a copy of the pending non-shadow orders."""
        return [order for order in self.position_manager.orders if not order.is_shadow]

    def get_increase_orders(self, source: Order | Trade):
        """Return non-shadow increase orders linked to the given source."""
        return [order for order in self.position_manager.increase_orders if order.source_id == source.id and not order.is_shadow]

    def get_stop_orders(self, source: Order | Trade):
        """Return non-shadow stop orders linked to the given source."""
        return [order for order in self.position_manager.stop_orders if order.source_id == source.id and not order.is_shadow]
    
    def get_take_profits(self, source: Order | Trade):
        """Return a list of take profit orders linked to the given source."""
        return [o for o in self.get_stop_orders(source) if isinstance(o, TakeProfit)]
    
    def get_stop_losses(self, source: Order | Trade):
        """Return a list of stop loss orders linked to the given source."""
        return [o for o in self.get_stop_orders(source) if isinstance(o, StopLoss)]

    def get_next_trade(self):
        """Return the first active trade, if available."""
        return next((t for t in self.get_trades()), None)
    
    def get_next_order(self):
        """Return the first pending order, if available."""
        return next((t for t in self.get_orders()), None)
    
    def get_next_increase_order(self, source: Order | Trade):
        """Return the first increase order linked to the given source, if available."""
        return next((t for t in self.get_increase_orders(source)), None)
    
    def get_next_take_profit(self, source: Order | Trade):
        """Return the first take profit order linked to the given source, if available."""
        return next((t for t in self.get_take_profits(source)), None)
    
    def get_next_stop_loss(self, source: Order | Trade):
        """Return the first stop loss order linked to the given source, if available."""
        return next((t for t in self.get_stop_losses(source)), None)

    # order book queries

    def get_best_bid(self):
        """Return the best bid price from the order book."""
        return self.order_book.best_bid
    
    def get_best_ask(self):
        """Return the best ask price from the order book."""
        return self.order_book.best_ask

    def get_spread(self):
        """Return the spread from the order book."""
        return self.order_book.spread

    # data provider queries

    def get_current_symbol(self):
        """Return the current instrument symbol."""
        return DataProvider().get_symbol()

    def get_current_price(self):
        """Return the latest market price."""
        return DataProvider().get_price()
    
    def get_current_time(self):
        """Return the latest market timestamp."""
        return DataProvider().get_time()

    # timestamp queries

    def get_datetime(self, timestamp: int | None = None) -> datetime:
        """Convert a timestamp to a datetime using the current time."""
        timestamp = self.get_current_time() if timestamp is None else timestamp
        return datetime.fromtimestamp(timestamp / 1000)

    def is_weekday(self, timestamp: int | None = None) -> bool:
        """Return whether the given timestamp falls on a weekday."""
        return self.get_datetime(timestamp).weekday() < 5

    def get_weekday(self, timestamp: int | None = None) -> int:
        """Return the weekday (0=Monday, 6=Sunday) for the given timestamp."""
        return self.get_datetime(timestamp).weekday()

    def get_hour(self, timestamp: int | None = None) -> int:
        """Return the hour (0-23) for the given timestamp."""
        return self.get_datetime(timestamp).hour

    def get_minute(self, timestamp: int | None = None) -> int:
        """Return the minute (0-59) for the given timestamp."""
        return self.get_datetime(timestamp).minute

    # session context queries

    def get_price_distance(self, ticks: int | Decimal) -> Decimal:
        """Convert a tick distance to the corresponding price distance."""
        metadata = self.session_pair_context.get_instrument_metadata()

        return Decimal(str(ticks)) * metadata.tick_size

    # resource queries

    def get_resource(self, name: str, model_type: type[ModelT]) -> ModelT | None:
        """Return a resource model when it matches the requested type."""
        resource = self.session_pair_context.get_resource(name)
        return resource if isinstance(resource, model_type) else None