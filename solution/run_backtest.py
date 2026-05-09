"""
Скрипт для ручного запуска бэктеста.

Примеры:
    python run_backtest.py                              # AS-2008 default на sample
    python run_backtest.py --strategy baseline
    python run_backtest.py --strategy microprice
    python run_backtest.py --gamma 0.3 --T 1.0          # свои параметры AS
    python run_backtest.py --full                       # на полных данных вместо sample
    python run_backtest.py --plot                       # вывести графики PnL/inventory
"""
from __future__ import annotations
import argparse
import time
from pathlib import Path

from src.config import EngineConfig, StrategyConfig
from src.engine import BacktestEngine
from src.reader import stream_events
from src.strategies import (
    AvellanedaStoikov2008,
    BaselineStrategy,
    make_microprice_strategy,
)


ROOT = Path(__file__).parent
DATA_SAMPLE = ROOT / "data" / "MD" / "sample"
DATA_FULL = ROOT / "data" / "MD"


def build_strategy(name: str, args) -> object:
    if name == "baseline":
        return BaselineStrategy(
            half_spread_fp=args.half_spread_fp,
            size=args.order_size,
        )

    cfg = StrategyConfig(
        gamma=args.gamma,
        k=args.k,
        sigma=args.sigma,
        T=args.T,
        order_size=args.order_size,
        max_inventory=args.max_inventory,
    )

    if name == "as2008":
        return AvellanedaStoikov2008(cfg)
    if name == "microprice":
        return make_microprice_strategy(cfg)

    raise ValueError(f"Unknown strategy: {name}")


def print_summary(name: str, metrics, elapsed: float) -> None:
    s = metrics.summary()
    print(f"\n=== {name} ===")
    print(f"  final_pnl       = {s['final_pnl']:>14,.2f}")
    print(f"  final_inventory = {s['final_inventory']:>14,.2f}")
    print(f"  final_cash      = {s['final_cash']:>14,.2f}")
    print(f"  turnover        = {s['turnover']:>14,.2f}")
    print(f"  n_fills         = {s['n_fills']:>14}")
    print(f"  final_mid       = {s['final_mid']:>14,.4f}" if s['final_mid'] else "")
    print(f"  elapsed         = {elapsed:.2f}s")


def maybe_plot(metrics, name: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не установлен, пропускаю графики")
        return

    if not metrics.ts_log:
        print("Нет данных для графика (mtm пустой)")
        return

    ts_s = [(t - metrics.ts_log[0]) / 1e6 for t in metrics.ts_log]

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(ts_s, metrics.pnl_log)
    axes[0].set_ylabel("PnL")
    axes[0].set_title(f"{name}")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(ts_s, metrics.inv_log, color="tab:orange")
    axes[1].set_ylabel("Inventory")
    axes[1].axhline(0, color="k", linewidth=0.5)
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(ts_s, metrics.mid_log, color="tab:green")
    axes[2].set_ylabel("Mid")
    axes[2].set_xlabel("Время, с")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategy",
        choices=["baseline", "as2008", "microprice", "all"],
        default="as2008",
    )
    parser.add_argument("--full", action="store_true", help="полные данные вместо sample")
    parser.add_argument("--plot", action="store_true", help="графики PnL/inv/mid")

    parser.add_argument("--gamma", type=float, default=0.1)
    parser.add_argument("--k", type=float, default=1.5)
    parser.add_argument("--sigma", type=float, default=18.18)
    parser.add_argument("--T", type=float, default=0.1)
    parser.add_argument("--order-size", type=float, default=1000.0)
    parser.add_argument("--max-inventory", type=float, default=20.0)

    parser.add_argument("--half-spread-fp", type=int, default=2,
                        help="только для baseline")

    parser.add_argument("--requote-ms", type=int, default=100)
    parser.add_argument("--mtm-ms", type=int, default=1000)

    args = parser.parse_args()

    data_dir = DATA_FULL if args.full else DATA_SAMPLE
    lob_path = str(data_dir / "lob.csv")
    trd_path = str(data_dir / "trades.csv")
    print(f"data: {data_dir}")

    engine_cfg = EngineConfig(
        requote_interval_us=args.requote_ms * 1000,
        mtm_interval_us=args.mtm_ms * 1000,
    )

    names = ["baseline", "as2008", "microprice"] if args.strategy == "all" else [args.strategy]

    results: dict[str, object] = {}
    for name in names:
        strategy = build_strategy(name, args)
        engine = BacktestEngine(strategy=strategy, cfg=engine_cfg)
        events = stream_events(lob_path, trd_path)

        t0 = time.time()
        metrics = engine.run(events)
        elapsed = time.time() - t0

        print_summary(name, metrics, elapsed)
        results[name] = metrics

        if args.plot:
            maybe_plot(metrics, name)


if __name__ == "__main__":
    main()
