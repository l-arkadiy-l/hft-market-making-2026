"""
PnL = cash + inventory * mid.
"""
from .config import to_float


class Trade:
    def __init__(self, ts_us: int, side: str, price_fp: int, size: float):
        self.ts_us = ts_us
        self.side = side
        self.price_fp = price_fp
        self.size = size

    def __repr__(self):
        return (f"Trade(ts={self.ts_us}, {self.side}, "
                f"price={self.price_fp}, size={self.size})")


class Metrics:
    def __init__(self):
        self.cash: float = 0.0
        self.inventory: float = 0.0
        self.turnover: float = 0.0
        self.trades: list[Trade] = []

        self.ts_log: list[int] = []
        self.pnl_log: list[float] = []
        self.inv_log: list[float] = []
        self.mid_log: list[float] = []

    def record_fill(self, ts_us: int, side: str, price_fp: int, size: float) -> None:
        price = to_float(price_fp)
        if side == 'B':
            self.cash -= price * size
            self.inventory += size
        else:
            self.cash += price * size
            self.inventory -= size
        self.turnover += size
        self.trades.append(Trade(ts_us, side, price_fp, size))

    def mark_to_market(self, ts_us: int, mid_price: float) -> float:
        pnl = self.cash + self.inventory * mid_price
        self.ts_log.append(ts_us)
        self.pnl_log.append(pnl)
        self.inv_log.append(self.inventory)
        self.mid_log.append(mid_price)
        return pnl

    def summary(self, final_mid: float | None = None) -> dict:
        if final_mid is None and self.mid_log:
            final_mid = self.mid_log[-1]
        final_pnl = self.cash + (self.inventory * final_mid if final_mid else 0.0)
        return {
            'final_pnl': final_pnl,
            'final_inventory': self.inventory,
            'final_cash': self.cash,
            'turnover': self.turnover,
            'n_fills': len(self.trades),
            'final_mid': final_mid,
        }
