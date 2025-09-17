# System Design

## Core Components
- **Screener**: Provider abstraction (Yahoo default, TV optional).
- **Analyzer**: Pattern classifier (rule-based + ML).
- **Strategy Engine**: Maps to buckets/timeslots.
- **Execution Engine**: Alpaca API integration.
- **Backtester**: QuantConnect Lean engine.
- **Infra**: AWS EKS cluster.

## Data Flow

Data Providers → Screener → Analyzer → Strategy Engine → Execution → Journal Logs (S3 + DynamoDB)

## AWS Infra
- **EKS**: services per module.
- **S3**: store artifacts/reports.
- **RDS (Postgres)**: portfolio/trade logs.
- **Secrets Manager**: Alpaca API keys.
- **CloudWatch/Prometheus**: monitoring.

## Providers
- `YahooProvider` → OHLCV, fundamentals.
- `TradingViewProvider` (optional).
- `QuantConnectProvider` for historical data/backtests.

## Execution
- **Alpaca REST/WS API**:
  - Submit/cancel orders.
  - Stream trades/positions.
- Support paper/live mode.