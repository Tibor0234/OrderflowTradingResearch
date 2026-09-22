from strategies.core.essentials import *

class TestStrategy(BaseStrategy):
    def on_candle_close(self, candle_sec):
        vd_1m = self.fw.get_resource("vd_1m", VolumeDelta)
        
        if len(vd_1m.history) == 0 or vd_1m.history[-1] is None:
            return

        if not self.fw.is_trade_open() and not self.fw.is_order_pending():

            if vd_1m.history[-1].value > Decimal(0):
                self.fw.place_market_order(
                    side=1,
                    value=1000,
                    leverage=10,
                    metadata={"entry_reason": "vd_1m positive"}
                )

        else:
            if vd_1m.history[-1].value < Decimal(0):
                self.fw.place_reduce_only_order(
                    source=self.fw.get_next_trade(),
                    pct=100,
                    metadata={"exit_reason": "vd_1m negative"}
                )