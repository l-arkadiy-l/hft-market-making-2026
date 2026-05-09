# HFT School Backtester - Avellaneda-Stoikov market-making

Добрый день, предоставляю мое решение экзамена.

## Что где (по пунктам ТЗ)

**Backtester:**
- Integrated backtest engine - `src/engine.py` (event loop + trade-based matching)
- Sample dataset - `data/MD/sample/` (1 час, ~7k LOB snaps, ~58k trades)
- Configs - `configs/default.yaml` (параметры всех стратегий и grid sweep'а)
- Performance report - `notebooks/report.ipynb`
- Technical documentation - см. "Архитектура" ниже

**Strategy:**
- Source code - `src/strategies.py` (Baseline, AvellanedaStoikov2008, microprice)
- Model description - см. "Алгоритм Avellaneda-Stoikov 2008"
- Performance results - `notebooks/report.ipynb`
- Improvement roadmap - см. "Калибровка sigma" и "Расширения базовой модели"

## Что внутри

```
src/
  config.py       PRICE_SCALE, EngineConfig, StrategyConfig
  reader.py       Stream LOB+trades CSV, k-way merge по timestamp
  lob.py          LimitOrderBook: bids/asks, mid, microprice, imbalance
  orders.py       OrderManager: place / cancel / track
  metrics.py      cash, inventory, PnL, fills, time-series
  engine.py       Event loop. Trade-based matching.
  strategies.py   BaselineStrategy, AvellanedaStoikov2008, microprice variant

notebooks/
  report.ipynb    Бэктест трёх стратегий, подбор параметров, графики

configs/
  default.yaml    Параметры стратегий, движка, grid sweep'а

data/MD/          Полные LOB+trades CSV
data/MD/sample/   Урезанный кусок для быстрого dev
```

## Архитектура

```
data/MD/sample/lob.csv     ──┐
data/MD/sample/trades.csv  ──┴── reader.stream_events (k-way merge по ts)
                                        │
                                        ▼
                                BacktestEngine
                                ├── snap  -> LOB.apply_snapshot
                                │           -> Strategy.on_market_event (раз в 100ms)
                                │           -> OrderManager (place/cancel)
                                │           -> Metrics.mark_to_market (раз в 1s)
                                │
                                └── trade -> match_against_trade
                                            -> Metrics.record_fill
                                            -> Strategy.on_fill
```

**Жизненный цикл итерации `BacktestEngine.run()`:**

1. Читаем событие `(ts, kind, data)` из стримящего ридера (без загрузки в память).
2. Если `kind == 'snap'`:
   - `lob.apply_snapshot(data)` обновляет top-25 уровней.
   - `_maybe_requote(ts)`: раз в 100ms просим стратегию пересчитать котировки,
     старые ордера снимаем, новые ставим.
   - `_maybe_mtm(ts)`: раз в 1s пишем PnL в time-series.
3. Если `kind == 'trade'`:
   - Проходим по активным ордерам, исполняем тех у кого цена совпадает с
     направлением сделки. Размер fill'а ограничен размером trade'а
     (без queue position).

**Контракт стратегии:**
- `on_market_event(ts_us, lob) -> list[(side, price_fp, size)]` - возвращает котировки
- `on_fill(ts_us, side, price_fp, size, lob) -> None` - колбэк после исполнения

**Fixed-point цены:** все цены `int` с `PRICE_SCALE = 10_000_000`. Tick 1e-7 float = 1 fp.
Так избегаем floating-point ошибок в сравнениях.

**Trade-based matching:** наш лимит исполняется только если реальный trade прошёл
через его уровень. Консервативная модель без queue position. Альтернатива (fill
при сдвиге best price) переоценивает fill rate.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name=hft_backtester
```

Открыть `notebooks/report.ipynb`, выбрать kernel `hft_backtester`, run all.

**Все графики, таблицы и анализ - в `notebooks/report.ipynb`:**
- Калибровка sigma из mid-price returns
- Сравнение трёх стратегий (baseline, AS-2008, microprice)
- Декомпозиция PnL: spread vs direction
- Grid sweep по gamma, T, k с heatmap'ами
- Графики std(inv), n_fills, Sharpe vs gamma и T
- Финальный прогон с лучшими параметрами
- Выводы

## Алгоритм Avellaneda-Stoikov 2008

```
r       = s - q * gamma * sigma^2 * tau
spread  = gamma * sigma^2 * tau + (2/gamma) * ln(1 + gamma/k)
bid     = r - spread/2
ask     = r + spread/2
```

- `s`     - fair price (mid или microprice)
- `q`     - инвентарь в лотах (1 лот = `order_size`)
- `gamma` - risk aversion (CARA-utility)
- `sigma` - реализованная волатильность mid в fp / sqrt(second)
- `k`     - параметр интенсивности исполнения, lambda(d) = A * exp(-k*d)
- `tau`   - rolling const = `cfg.T`. Эквивалент бесконечного горизонта
            с дисконтом omega = 1/tau (раздел 2.3 статьи).

Inventory разгружается **пассивно**: при `q > 0` reservation price идёт вниз
-> ask становится ближе к рынку -> рынок выкупает позицию.
Жёсткий лимит `max_inventory` снимает одну сторону при превышении.

## Калибровка sigma

Сейчас sigma вычисляется один раз из всего sample. В реальности
её надо оценивать онлайн. Варианты по нарастанию сложности:

- **Realized vol на rolling window** - простейший вариант. Sigma из последних
  N секунд. Окно 1-5 минут типично для HFT.
- **EWMA** (RiskMetrics 1996): sigma_t^2 = lambda * sigma_{t-1}^2 + (1-lambda) * r_t^2.
  При lambda=0.94 half-life шока ~ 11 периодов. Без явного окна,
  экспоненциально затухающие веса.
- **GARCH(1,1)**: sigma_t^2 = omega + alpha * r_{t-1}^2 + beta * sigma_{t-1}^2.
  Расширение EWMA с возвратом к долгосрочному среднему. Учитывает кластеризацию
  волатильности.
- **Two-scale realized variance** - корректирует на microstructure noise при
  субсекундных returns.
- **Bipower variation** - устойчиво к скачкам (jump-robust).

В StrategyConfig уже есть `sigma: float | None = None` под online-оценку,
осталось только добавить логику в стратегии.

## Расширения базовой модели

### Уже сделано
- **Microprice fair price** (Stoikov 2018) - `make_microprice_strategy()`.

### Классические расширения
- **Guéant, Lehalle, Tapia (2013)** - hard inventory cap |q| <= Q через систему
  ODE с граничным условием. Котировки становятся резко асимметричными у стенки.
- **Cartea, Jaimungal, Ricci (2014)** - alpha-сигнал (OFI/imbalance) в
  reservation price. Адверс-селекшен поправка.
- **Cartea, Jaimungal, Penalva (2015) "Algorithmic and HFT"** (книга) -
  систематический разбор multi-asset MM, latent factors, нелинейный импакт.
- **Bergault, Evangelista, Guéant, Vieira (2021)** - multi-asset MM с
  closed-form решением.

### Антиклассическое расширение
- **Lalor, Swishchuk (2024)** - RL-подход для non-Markov market making.

### TODO в этом проекте
- Empirical lambda(delta) калибровка из trades.csv (фит exp-distribution)
- OFI signal в reservation price
- Online sigma estimation (расписал в секции выше)
- Train/test split вместо тестирования на тех же данных где подбирали параметры
