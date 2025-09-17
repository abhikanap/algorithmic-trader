# Development Roadmap

## Phase 1 – Screener
- Data ingestion (Yahoo Finance primary, optional TradingView).
- Volatility metrics: ATR%, HV, VWAP, gap %, dollar volume.
- Output artifacts: parquet + jsonl + report.md.

## Phase 2 – Analyzer
- Intraday classification (patterns A–E).
- Multi-day classification.
- Technical indicators: RSI, MACD, ATR, Bollinger, VWAP.

## Phase 3 – Strategy Engine
- Capital allocation buckets.
- Timeslot playbook.
- Risk rules: max % per trade, trailing stops, ATR-based SL/TP.

## Phase 4 – Execution Engine
- Alpaca API integration (paper/live).
- Portfolio balancer (intraday rebalancing).
- Logging to S3 + Postgres (AWS RDS).

## Phase 5 – Backtesting
- QuantConnect integration (Lean engine).
- Replay historical intraday + swing setups.
- Evaluate PnL by bucket, Sharpe, drawdown.

## Phase 6 – Deployment
- Modular microservices on **AWS EKS**.
- S3 artifact storage, CloudWatch logging.
- CI/CD via GitHub Actions → EKS rollout.

## Phase 7 – AI/LLM/VLM Layer
- Use LLMs to interpret intraday context & news.
- VLMs for chart recognition.
- Adaptive allocation: agent adjusts bucket weights.