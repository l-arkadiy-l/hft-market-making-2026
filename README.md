# CMF HFT Market-Making Backtester — submission

## Решение

Реализовано на **Python**. Лежит в папке [`solution/`](./solution/) этого форка.

**Зеркало в отдельном репозитории:** https://github.com/l-arkadiy-l/HFT_exam

### Что внутри `solution/`

```
solution/
├── README.md            описание архитектуры, формул AS-2008, калибровки sigma, roadmap
├── run_backtest.py      CLI запуск бэктеста
├── requirements.txt     зависимости (pandas, numpy, matplotlib, jupyter)
├── configs/
│   └── default.yaml     параметры стратегий и grid sweep
├── src/
│   ├── config.py        PRICE_SCALE, EngineConfig, StrategyConfig
│   ├── reader.py        стриминг tardis.dev CSV, k-way merge по timestamp
│   ├── lob.py           LimitOrderBook (bids/asks, mid, microprice, imbalance)
│   ├── orders.py        OrderManager (place / cancel / track)
│   ├── metrics.py       cash, inventory, PnL, fills, time-series
│   ├── engine.py        event loop + trade-based matching
│   └── strategies.py    BaselineStrategy, AvellanedaStoikov2008, microprice variant
├── notebooks/
│   └── report.ipynb     полный performance-отчёт со всеми графиками
└── data/MD/sample/      sample dataset (1 час, ~7k LOB snaps, ~58k trades)
```

Полные данные (1.8 GB) не закоммичены, они gitignore'нуты — кладутся локально в `solution/data/MD/`.

### Запуск

```bash
cd solution
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Бэктест из CLI
.venv/bin/python run_backtest.py --strategy as2008 --data data/MD/sample

# Полный отчёт
.venv/bin/python -m ipykernel install --user --name=hft_backtester
# → открыть notebooks/report.ipynb с этим kernel и run all
```

Подробности и анализ — в [solution/README.md](./solution/README.md).

---

## Original CMF C++ scaffold

Оригинальный C++ scaffold из upstream сохранён (`cmake/`, `src/`, `test/`,
`CMakeLists.txt`), но не использовался — решение целиком на Python
(Python Alternative Path, см. submission instructions).
