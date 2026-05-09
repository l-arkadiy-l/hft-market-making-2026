# CMF HFT Market-Making Backtester — submission

Решение реализовано на **Python** в отдельном репозитории:

### → https://github.com/l-arkadiy-l/HFT_exam

Там лежит:
- `src/` — backtester engine, LOB, orders, metrics, reader
- `src/strategies.py` — Baseline, Avellaneda-Stoikov 2008, microprice variant
- `notebooks/report.ipynb` — performance report со всеми графиками и анализом
- `configs/default.yaml` — конфиги стратегий и grid sweep
- `data/MD/sample/` — sample dataset
- `README.md` — описание архитектуры, формул AS-2008, калибровки sigma, roadmap

Инструкции по запуску — в README того репозитория.

---

## Original CMF C++ scaffold

Оригинальный C++ scaffold из upstream сохранён в этом fork-е (`cmake/`, `src/`, `test/`),
но не использовался — решение целиком на Python (Python Alternative Path,
см. submission instructions).
