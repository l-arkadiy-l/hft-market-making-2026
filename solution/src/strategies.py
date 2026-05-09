"""
Стратегии market-making.
"""
from .config import StrategyConfig, PRICE_SCALE
from .lob import LimitOrderBook
from math import log


class BaselineStrategy:
    """
    Котирует bid и ask симметрично вокруг mid с фикс. полуспредом.
    """

    def __init__(self, half_spread_fp: int = 2, size: float = 1000.0):
        self.half_spread_fp = half_spread_fp
        self.size = size
        self.q = 0.0

    def on_market_event(self, ts_us, lob: LimitOrderBook):
        if not lob.is_ready():
            return []

        mid_fp = lob.mid_fp()
        if mid_fp is None:
            return []

        bid_fp = mid_fp - self.half_spread_fp
        ask_fp = mid_fp + self.half_spread_fp

        best_bid = lob.best_bid()
        best_ask = lob.best_ask()
        if best_ask is not None and bid_fp >= best_ask[0]:
            bid_fp = best_ask[0] - 1
        if best_bid is not None and ask_fp <= best_bid[0]:
            ask_fp = best_bid[0] + 1

        return [
            ('B', bid_fp, self.size),
            ('A', ask_fp, self.size),
        ]

    def on_fill(self, ts_us, side, price_fp, size, lob):
        if side == 'B':
            self.q += size
        else:
            self.q -= size


class AvellanedaStoikov2008:
    """
    Avellaneda & Stoikov (2008).

    r      = s - q*gamma*sigma^2*tau
    spread = gamma*sigma^2*tau + (2/gamma)*ln(1 + gamma/k)
    bid = r - spread/2,  ask = r + spread/2

    tau - rolling const.
    """

    def __init__(self, cfg: StrategyConfig, fair_price_fn=None):
        self.cfg = cfg
        self.q = 0.0
        self._fair_price_fn = fair_price_fn or (lambda lob: lob.mid_fp())

    def on_market_event(self, ts_us, lob):
        if not lob.is_ready():
            return []

        s = self._fair_price_fn(lob)
        if s is None or self.cfg.sigma is None:
            return []

        gamma = self.cfg.gamma
        sigma = self.cfg.sigma
        k = self.cfg.k
        tau = self.cfg.T

        r = s - self.q * gamma * sigma ** 2 * tau
        spread = gamma * sigma ** 2 * tau + (2 / gamma) * log(1 + gamma / k)
        half = spread / 2

        bid_fp = int(round(r - half))
        ask_fp = int(round(r + half))

        best_bid = lob.best_bid()
        best_ask = lob.best_ask()
        if best_ask is not None and bid_fp >= best_ask[0]:
            bid_fp = best_ask[0] - 1
        if best_bid is not None and ask_fp <= best_bid[0]:
            ask_fp = best_bid[0] + 1

        orders = []
        if self.q < self.cfg.max_inventory:
            orders.append(('B', bid_fp, self.cfg.order_size))
        if self.q > -self.cfg.max_inventory:
            orders.append(('A', ask_fp, self.cfg.order_size))
        return orders

    def on_fill(self, ts_us, side, price_fp, size, lob):
        # q в лотах (1 лот = order_size), как в статье где q меняется на +-1
        lots = size / self.cfg.order_size
        if side == 'B':
            self.q += lots
        else:
            self.q -= lots


def make_microprice_strategy(cfg: StrategyConfig):
    """AS-2008 с fair price = microprice (Stoikov 2018)."""
    def fair_price_fn(lob):
        mp = lob.microprice()
        if mp is None:
            return lob.mid_fp()
        return int(round(mp * PRICE_SCALE))

    return AvellanedaStoikov2008(cfg, fair_price_fn=fair_price_fn)
