from strategies.core.essentials import *

class TestStrategy(BaseStrategy):
    def on_candle_close(self, candle_sec):
        if self.fw.is_trade_open() or self.fw.is_order_pending():
            return

        tf_1m = self.fw.get_resource("tf_1m", Timeframe)
        cvd_1m = self.fw.get_resource("cvd_1m", VolumeDelta)
        vp_1m = self.fw.get_resource("vp_1m", VolumeProfile)
        
        value_area = vp_1m.value_area

        va_10pct = (value_area.high - value_area.low) * Decimal(0.05)
        va_low_max = value_area.low + va_10pct
        va_high_min = value_area.high - va_10pct
        trend_strength = queries.get_trend_strength(tf_1m.content, "close", 0)
        price = self.fw.get_current_price()

        if abs(trend_strength) > 0.2:
            return

        if value_area.low <= price <= va_low_max:
            order = self.fw.place_market_order(
                side=Side.BUY,
                value=1000,
                leverage=10,
                metadata={"entry_reason": "price within value area low range",
                          "trend_strength": trend_strength
                        }
            )

            self.fw.place_take_profit_market(
                source=order,
                price=va_high_min,
                pct=100,
                metadata={"take_profit_reason": "price reached value area high minimum"}
            )

            self.fw.place_stop_loss(
                source=order,
                price=value_area.low - va_10pct * 4,
                metadata={"stop_loss_reason": "price reached below value area low"}
            )
            
        elif va_high_min <= price <= value_area.high:
            order = self.fw.place_market_order(
                side=Side.SELL,
                value=1000,
                leverage=10,
                metadata={"entry_reason": "price within value area high range",
                          "trend_strength": trend_strength
                        }
            )

            self.fw.place_take_profit_market(
                source=order,
                price=va_low_max,
                pct=100,
                metadata={"take_profit_reason": "price reached value area low maximum"}
            )

            self.fw.place_stop_loss(
                source=order,
                price=value_area.high + va_10pct * 4,
                metadata={"stop_loss_reason": "price reached above value area high"}
            )