from strategies.core.essentials import *

class TestStrategy(BaseStrategy):

    def on_candle_close(self, candle_sec):
        
        if self.fw.is_trade_open() or self.fw.is_order_pending():
            return

        vp = self.fw.get_resource('vp_1m', VolumeProfile)
        tf = self.fw.get_resource('tf_1m', Timeframe)

        has_min_length = queries.has_min_length(tf.content, 100)

        if not has_min_length:
            return

        hvns = volume_profile_queries.get_high_volume_nodes(vp, threshold_ratio=0.7)
        lvns = volume_profile_queries.get_low_volume_nodes(vp, threshold_ratio=0.4)
        valleys = volume_profile_queries.get_bracketed_low_volume_nodes(hvns, lvns)

        if valleys:
            return
        
        if tf.content[-3].open < vp.value_area.high and tf.content[-3].close > vp.value_area.high \
            and tf.content[-2].close < vp.value_area.high \
                and tf.content[-1].close < vp.value_area.high \
                    and tf.content[-1].close > vp.poc.price:
            
            order = self.fw.place_limit_order(
                side = -1,
                margin = 1000,
                entry_price = tf.content[-1].open,
                leverage=10,
            )

            va_range = vp.value_area.high - vp.value_area.low
            sl_price = vp.value_area.high + va_range * Decimal(0.1)

            self.fw.place_stop_loss(
                source=order,
                price=sl_price,
                pct=75,
                metadata={"Stop: Exit Reason": "Stop Loss",
                          "asd": 1}
            )

            #tp_price = vp.value_area.low + va_range * Decimal(0.1)

            self.fw.place_take_profit_limit(
                source=order,
                price=vp.poc.price,
                pct=75,
                metadata={"Stop: Exit Reason": "Take Profit",
                          "asd": 3}
            )

        elif tf.content[-3].open > vp.value_area.low and tf.content[-3].close < vp.value_area.low \
            and tf.content[-2].close > vp.value_area.low \
                and tf.content[-1].close > vp.value_area.low \
                    and tf.content[-1].close < vp.poc.price:
            order = self.fw.place_limit_order(
                side = 1,
                margin = 1000,
                entry_price = tf.content[-1].open,
                leverage=10,
            )

            va_range = vp.value_area.high - vp.value_area.low
            sl_price = vp.value_area.low - va_range * Decimal(0.1)

            self.fw.place_stop_loss(
                source=order,
                price=sl_price,
                pct=50,
                metadata={"Stop: Exit Reason": "Stop Loss",
                          "asd": 2}
            )

            #tp_price = vp.value_area.high - va_range * Decimal(0.1)

            self.fw.place_take_profit_limit(
                source=order,
                price=vp.poc.price,
                pct=50,
                metadata={"Stop: Exit Reason": "Take Profit",
                          "asd": 4}
            )

        