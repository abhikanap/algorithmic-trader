You are a senior Python engineer building a modular algorithmic trading platform.
Use the repository’s Markdown docs as the source of truth. Implement the codebase to match them.

READ THESE DOCS FIRST (in order):
1) README.md  (root, “Master Blueprint”)
2) strategy/README_STRATEGY.md  (patterns, buckets, time segments)
3) planning/README_PLANNING.md  (phased roadmap)
4) design/README_DESIGN.md  (system architecture, AWS EKS, providers)
5) execution/README_EXECUTION.md  (Alpaca integration, portfolio rebalancing)
6) testing/README_TESTING.md  (unit/integration/backtest plans)
7) integration/README_INTEGRATION.md  (Alpaca, QuantConnect, AWS EKS, dashboards)
8) future/README_IDEATION.md  (AI/LLM/VLM ideas for later)
Also treat the reference strategy notes in strategy/ (Intraday Patterns.md, Day Trading Strategy by Intraday Time Segments and Capital Buckets.pdf, Comprehensive Classification of Stock Movement Patterns and Trading Strategies.pdf) as background guidance for naming, enums, and defaults.

=== OBJECTIVE ===
Implement Phase 1 end-to-end and scaffold Phases 2–6 so they run, test, and deploy locally and in CI. Phase 1 is the Screener (Yahoo provider default). Provide stubs for Analyzer and Strategy Engine that consume Screener artifacts. Add Alpaca & QuantConnect integrations behind feature flags. Prepare AWS EKS deploy assets.

=== TECH & CONSTRAINTS ===
- Python 3.11+
- Data: yfinance (Yahoo). TradingView optional (feature-flag, provider adapter, no hard dependency). Respect ToS.
- Execution: Alpaca REST/WS (sandbox first). Keys via env/Secrets.
- Backtesting: QuantConnect Lean (Dockerized, wiring + example algo stub).
- Storage: S3 (artifacts), Postgres/RDS (positions/trades), local dev uses filesystem + SQLite fallback.
- Orchestration: Makefile targets. CI with GitHub Actions.
- Deployment: AWS EKS (Helm chart or K8s manifests + values), minimal but functional.
- Config-driven, type-safe (pydantic). Structured logging. Unit tests + golden tests.

=== REPO LAYOUT (CREATE/CONFIRM) ===
apps/
  screener/                # Phase-1
    __init__.py
    cli.py                 # click-based CLI
    pipeline.py            # orchestrates run
    providers/
      base.py              # Provider protocol
      yahoo.py             # yfinance implementation
      tv.py                # optional TradingView adapter (feature-flag)
    features.py            # ATR, HV, range%, gap%, etc.
    filters.py             # liquidity/volatility gates
    ranking.py             # sort logic, sector caps
    artifacts.py           # parquet/jsonl/report writers
  analyzer/                # Phase-2 (stub but runnable)
    __init__.py
    cli.py
    classify_intraday.py   # rule-based patterns (stub)
    classify_multiday.py   # stub
    schema.py              # Pydantic IO schema from Screener
  strategy/                # Phase-3 (scaffold)
    __init__.py
    cli.py
    buckets.py             # enums + config mapping
    allocator.py           # capital split by bucket & timeslot (stub)
  execution/               # Phase-4 (scaffold)
    __init__.py
    cli.py
    alpaca_client.py       # wrapper (paper by default)
    portfolio.py           # rebalancing rules (stub)
  backtesting/             # Phase-5 (scaffold)
    __init__.py
    lean/                  # Dockerfile + sample project wiring
      Dockerfile
      config.json
      strategies/
        sample_algo.py
packages/
  core/
    __init__.py
    models.py              # shared dataclasses/pydantic models
    time_slots.py          # 9:30–10:30, 10:30–13:30, 13:30–15:00, 15:00–16:00
    constants.py
    logging.py
  data/
    __init__.py
    cache.py               # on-disk cache
    io.py                  # S3/local parquet helpers
  indicators/
    __init__.py
    atr.py
    hv.py
    rsi.py
    moving_averages.py
infra/
  docker/
    Dockerfile.api
    Dockerfile.lean
  k8s/                     # OR helm/ if you prefer Helm
    deployment.yaml
    service.yaml
    configmap.yaml
    secret.yaml            # use placeholders; docs explain fetching from AWS Secrets Manager
  ci/
    github-actions.yml
config/
  .env.example
  screener.yaml
  strategy.yaml
  logging.yaml
tests/
  unit/
  integration/
  golden/
docs/                       # generated reports can live here or under artifacts/
strategy/
  README_STRATEGY.md
  INDEX.md                  # summarize & link the attached PDFs/MD
  Intraday Patterns.md
  Day Trading Strategy by Intraday Time Segments and Capital Buckets.pdf
  Comprehensive Classification of Stock Movement Patterns and Trading Strategies.pdf
artifacts/                  # gitignored
Makefile
pyproject.toml (or poetry/uv config)
README.md (root, master blueprint)
ui/
  app.py               # main dashboard
  pages/
    1_Screener.py
    2_Analyzer.py
    3_Strategy.py
    4_Execution.py
    5_Backtests.py
    6_Settings.py
  utils/
    data.py            # load artifacts, schemas, cache
    charts.py          # plotly helpers (candles, overlays)
  README_UI.md
infra/docker/Dockerfile.ui
config/ui.yaml
Makefile targets: ui.run, ui.docker.build, ui.docker.push, ui.deploy

=== IMPLEMENTATION DETAILS ===
1) CONFIG
- Create pydantic-settings for env: provider flags, Alpaca keys, AWS/S3, DB URL, feature toggles.
- Provide config/*.yaml with sensible defaults aligned to docs (min price, min dollar volume, ATR period, HV windows, bucket splits, timeslot boundaries).

2) SCREENER (Phase-1, fully functional)
- Provider protocol in apps/screener/providers/base.py
  - fetch_universe() -> DataFrame[symbol, name, exchange, sector, industry]
  - fetch_timeseries(symbols, start, end) -> dict[symbol -> OHLCV DataFrame]
  - fetch_snapshot(symbols) -> DataFrame[last/open/high/low/volume]
- YahooProvider implementation using yfinance with polite rate limiting and caching.
- Feature engineering in features.py:
  - ATR(14), ATR% (ATR/price*100), HV(10/20) annualized, day range%, gap%.
  - RSI, SMA20/50/200 minimal set.
- Filters in filters.py based on README thresholds (dollar vol, price floor, volatility gates).
- Ranking in ranking.py (atrp_14 desc, then dollar vol, hv_20) + optional per-sector caps.
- Artifacts in artifacts.py:
  - parquet full table: artifacts/screener/YYYY-MM-DD/screener.parquet
  - jsonl top-K: artifacts/screener/YYYY-MM-DD/screener_top.jsonl
  - REPORT.md summary.
- CLI (cli.py):
  - run: full pipeline with options: --provider, --date, --symbols-file, --topk
  - premkt: snapshot/gap scan (graceful if provider doesn’t support)
  - export: convert parquet -> jsonl top-K

3) ANALYZER (Phase-2, stub but runnable)
- Input schema matches Screener outputs.
- classify_intraday.py: rule-based mapping (from strategy docs) to pattern enums.
- classify_multiday.py: placeholder returning neutral until fleshed out.
- Output: analyzer_top.jsonl + REPORT.md summarizing counts by pattern & bucket hint.

4) STRATEGY ENGINE (Phase-3, scaffold)
- buckets.py: enums for A–E with default capital weights from README.
- allocator.py: given patterns + time slot, propose bucket and target weight; return suggested position sizes. Leave advanced risk logic as TODO.

5) EXECUTION (Phase-4, scaffold)
- alpaca_client.py: thin wrapper (submit_market_order, submit_limit_order, cancel_order, get_positions).
- portfolio.py: placeholder rebalancer that prints intended actions when in DRY_RUN=true.
- Tag orders with bucket_id, pattern_id, timeslot.

6) BACKTESTING (Phase-5, scaffold)
- Lean Dockerfile and sample strategy that loads symbols from screener_top.jsonl and runs a simple ATR-based exit; wire to output CSV to artifacts/backtesting/.
- Document how to run Lean locally via Makefile.

7) INFRA & CI/CD (sane defaults)
- Dockerfile.api: builds runtime for apps/* services.
- K8s (or Helm) manifests with env vars, ConfigMap for YAMLs, Secret placeholders for keys.
- GitHub Actions pipeline:
  - lint (ruff/flake8), type-check (mypy), tests (pytest), build images, push to registry, deploy to EKS on main.

8) LOGGING, METRICS, ERRORS
- Use structured logging (json) and logging.yaml levels per module.
- Emit run metadata (start/end, counts, top symbols) to logs and markdown report.
- Gracefully handle data gaps and rate limits.

9) TESTS
- Unit: indicators (atr, hv), filters, ranking.
- Integration: small universe run end-to-end against sample cached data.
- Golden: freeze a sample date with known outputs to detect regressions.

10) STREAMLIT UI
- Default MODE=artifacts: load latest parquet/jsonl under artifacts/*; allow date override
- Screener page: filterable table; symbol drilldown with candlesticks, volume; overlay VWAP, SMA(20/50/200), RSI
- Analyzer page: bar chart by pattern; table with badges; action “send to Strategy Preview”
- Strategy page: render buckets A–E from config/strategy.yaml; sliders (session) for weights; preview allocations by timeslot; export preview json
- Execution page: DRY_RUN controls; Alpaca status; show intended orders with tags {bucket, pattern, timeslot}; submit only in PAPER mode
- Backtests page: equity curve, drawdown, heatmap; per-bucket stats
- Settings page: flip mode, feature flags, artifacts path; password gate via UI_PASSWORD env
- Use st.session_state + @st.cache_data for refresh; refresh_seconds from config/ui.yaml

=== ACCEPTANCE CRITERIA ===
- `make ui.run` starts Streamlit and displays Dashboard with KPIs and timeslot badge
- Screener loads parquet/jsonl and supports filtering + symbol drilldown with Plotly overlays
- Strategy preview exports json under artifacts/ui/YYYY-MM-DD/
- Execution page prints intended orders in DRY_RUN; submits in PAPER when enabled
- Backtests plots render from artifacts/backtesting files
- `make ui.docker.build` and `make ui.deploy` work with provided manifests

Proceed to:
1) Generate folder structure, Makefile targets, Dockerfile.ui, config/ui.yaml
2) Implement UI data loaders (artifacts mode), schemas, and Plotly charting
3) Build pages exactly as specified in README_UI.md
4) Keep code typed & documented; reference readme sections in docstrings

=== ACCEPTANCE CRITERIA ===
- `make screener.run` creates parquet/jsonl/REPORT.md under artifacts/screener/<date>/.
- `make analyzer.run` consumes screener outputs and emits pattern-labeled JSONL + REPORT.md.
- `make strategy.preview` prints bucket allocations by timeslot (no real orders).
- `make execution.dryrun` reads analyzer output and prints intended Alpaca orders with tags (no network if DRY_RUN=true).
- `make backtest.sample` runs Lean container and writes results to artifacts/backtesting/.
- `make test` passes with meaningful coverage.
- `make docker.build` and `make deploy.eks` succeed using provided k8s manifests (with placeholder secrets).
- Code conforms to repo docs and feature flags work (e.g., disable TV provider by default).

=== COMMANDS TO PROVIDE ===
- Makefile targets:
  - install, lint, typecheck, test
  - screener.run, analyzer.run, strategy.preview
  - execution.dryrun, backtest.sample
  - docker.build, docker.push, deploy.eks
- Example .env.example with ALPACA_KEY/SECRET, S3_BUCKET, DB_URL, FEATURE_TV=false.

=== STYLE ===
- Clean, typed Python with pydantic models. No long functions; keep modules cohesive.
- Docstrings reference the relevant README section.
- Fail fast on invalid config; log clear remediation hints.

Start by generating the folder structure, pyproject/poetry config, Makefile, and stubs, then implement Screener fully. Follow the README-defined schemas and thresholds. When in doubt, prefer the values and flow described in README.md and strategy/README_STRATEGY.md.