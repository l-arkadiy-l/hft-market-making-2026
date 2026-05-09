from .config import to_float, PRICE_SCALE
from functools import wraps


def requires_book(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.bids or not self.asks:
            return None
        return method(self, *args, **kwargs)
    return wrapper


class LimitOrderBook:
    def __init__(self):
        self.bids: list[tuple[int, float]] = []
        self.asks: list[tuple[int, float]] = []
        self.ts_us: int = 0

    def apply_snapshot(self, snap):
        self.bids = snap['bids']
        self.asks = snap['asks']
        self.ts_us = snap['ts_us']

    def best_bid(self):
        return self.bids[0] if self.bids else None

    def best_ask(self):
        return self.asks[0] if self.asks else None

    @requires_book
    def get_bb_ba(self):
        return self.bids[0], self.asks[0]

    @requires_book
    def mid_fp(self):
        price_bid, _ = self.bids[0]
        price_ask, _ = self.asks[0]
        return (price_bid + price_ask) // 2

    @requires_book
    def mid(self):
        price_bid, _ = self.bids[0]
        price_ask, _ = self.asks[0]
        return to_float((price_bid + price_ask) // 2)

    @requires_book
    def microprice(self):
        price_bid, quantity_bid = self.bids[0]
        price_ask, quantity_ask = self.asks[0]
        if quantity_bid + quantity_ask == 0:
            return self.mid()
        weighted_sum = price_bid * quantity_ask + price_ask * quantity_bid
        total_quantity = quantity_bid + quantity_ask
        return weighted_sum / total_quantity / PRICE_SCALE

    @requires_book
    def spread_fp(self):
        price_bid, _ = self.bids[0]
        price_ask, _ = self.asks[0]
        return price_ask - price_bid

    @requires_book
    def imbalance(self):
        _, quantity_bid = self.bids[0]
        _, quantity_ask = self.asks[0]
        if quantity_bid + quantity_ask == 0:
            return 0.0
        return (quantity_bid - quantity_ask) / (quantity_bid + quantity_ask)

    def is_ready(self):
        return bool(self.bids) and bool(self.asks)
