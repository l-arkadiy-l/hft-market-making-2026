"""
Event loop. Trade-based matching: лимит исполняется только если
реальный trade прошёл через его цену.
"""
from .lob import LimitOrderBook
from .orders import OrderManager
from .metrics import Metrics
from .config import EngineConfig


class BacktestEngine:
    def __init__(self, strategy, cfg: EngineConfig | None = None):
        self.lob = LimitOrderBook()
        self.orders = OrderManager()
        self.metrics = Metrics()
        self.strategy = strategy
        self.cfg = cfg if cfg is not None else EngineConfig()

        self._last_quote_ts: int = 0
        self._last_mtm_ts: int = 0
        self._n_events: int = 0

    def run(self, events) -> Metrics:
        for ts, kind, data in events:
            self._n_events += 1

            if kind == 'snap':
                self.lob.apply_snapshot(data)
                self._maybe_requote(ts)
                self._maybe_mtm(ts)

            elif kind == 'trade':
                self._match_against_trade(ts, data)
                self._maybe_mtm(ts)

        return self.metrics

    def _match_against_trade(self, ts_us: int, trade: dict) -> None:
        trade_side = trade['side']
        trade_price = trade['price']
        trade_size_left = trade['size']
        o_keys = self.orders.active.keys()
        for oid in list(o_keys):
            if trade_size_left <= 0:
                break

            order = self.orders.active.get(oid)
            if order is None:
                continue

            fill_size = 0.0

            if order.side == 'B' and trade_side == 'sell' and trade_price <= order.price:
                fill_size = min(order.remaining(), trade_size_left)
            elif order.side == 'A' and trade_side == 'buy' and trade_price >= order.price:
                fill_size = min(order.remaining(), trade_size_left)

            if fill_size > 0:
                self.metrics.record_fill(ts_us, order.side, order.price, fill_size)
                self.strategy.on_fill(ts_us, order.side, order.price, fill_size, self.lob)
                order.filled_size += fill_size
                trade_size_left -= fill_size
                if not order.is_active():
                    self.orders.cancel(oid)

    def _maybe_requote(self, ts_us: int) -> None:
        if not self.lob.is_ready():
            return
        if ts_us - self._last_quote_ts < self.cfg.requote_interval_us:
            return

        quotes = self.strategy.on_market_event(ts_us, self.lob)

        self.orders.cancel_all()
        if quotes:
            for side, price_fp, size in quotes:
                self.orders.place(side, price_fp, size, ts_us)

        self._last_quote_ts = ts_us

    def _maybe_mtm(self, ts_us: int) -> None:
        if ts_us - self._last_mtm_ts < self.cfg.mtm_interval_us:
            return
        mid = self.lob.mid()
        if mid is None:
            return
        self.metrics.mark_to_market(ts_us, mid)
        self._last_mtm_ts = ts_us
