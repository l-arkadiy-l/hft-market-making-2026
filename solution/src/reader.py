"""
Стрим LOB+trades csv в порядке timestamp'ов.
"""
from __future__ import annotations
import csv
from typing import Iterator

from .config import PRICE_SCALE


def parse_snap(row: list[str], n_levels: int = 25) -> dict:
    asks: list[tuple[int, float]] = []
    bids: list[tuple[int, float]] = []
    for i in range(n_levels):
        ap = row[2 + i * 4]
        as_ = row[3 + i * 4]
        bp = row[4 + i * 4]
        bs = row[5 + i * 4]
        if ap and as_:
            asks.append((int(round(float(ap) * PRICE_SCALE)), float(as_)))
        if bp and bs:
            bids.append((int(round(float(bp) * PRICE_SCALE)), float(bs)))
    return {
        'ts_us': int(row[1]),
        'bids': bids,
        'asks': asks,
    }


def parse_trade(row: list[str]) -> dict:
    return {
        'ts_us': int(row[1]),
        'side': row[2],
        'price': int(round(float(row[3]) * PRICE_SCALE)),
        'size': float(row[4]),
    }


def stream_events(
    lob_path: str,
    trades_path: str,
    n_levels: int = 25,
) -> Iterator[tuple[int, str, dict]]:
    with open(lob_path, newline='') as lob_f, open(trades_path, newline='') as trd_f:
        lob_r = csv.reader(lob_f)
        trd_r = csv.reader(trd_f)

        next(lob_r, None)
        next(trd_r, None)

        lob_row = next(lob_r, None)
        trd_row = next(trd_r, None)

        while lob_row is not None or trd_row is not None:
            lob_ts = int(lob_row[1]) if lob_row is not None else None
            trd_ts = int(trd_row[1]) if trd_row is not None else None

            take_lob = (
                lob_ts is not None
                and (trd_ts is None or lob_ts <= trd_ts)
            )

            if take_lob:
                yield lob_ts, 'snap', parse_snap(lob_row, n_levels)
                lob_row = next(lob_r, None)
            else:
                yield trd_ts, 'trade', parse_trade(trd_row)
                trd_row = next(trd_r, None)
