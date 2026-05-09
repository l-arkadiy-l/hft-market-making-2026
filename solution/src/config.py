"""
Конфиги и константы fixed-point.
"""

PRICE_SCALE = 10_000_000


def to_fp(price: float) -> int:
    return int(round(price * PRICE_SCALE))


def to_float(price_fp: int) -> float:
    return price_fp / PRICE_SCALE


class EngineConfig:
    def __init__(
        self,
        requote_interval_us: int = 100_000,
        mtm_interval_us: int = 1_000_000,
    ):
        self.requote_interval_us = requote_interval_us
        self.mtm_interval_us = mtm_interval_us


class StrategyConfig:
    def __init__(
        self,
        gamma: float = 0.1,
        k: float = 1.5,
        sigma: float | None = None,
        T: float = 1.0,
        order_size: float = 1000.0,
        max_inventory: float = 50_000.0,
    ):
        self.gamma = gamma
        self.k = k
        self.sigma = sigma
        self.T = T
        self.order_size = order_size
        self.max_inventory = max_inventory
