# Integration Guide

## Broker: Alpaca
- REST API for order submission.
- Websocket for live price & execution streams.
- Paper/live modes.
- Store keys in AWS Secrets Manager.

## Backtesting: QuantConnect
- Use Lean engine in Docker on AWS.
- Strategy definitions synced from `/strategies/`.
- Results exported to S3.

## Cloud: AWS EKS
- Each module = containerized service.
- CI/CD via GitHub Actions → EKS rollout.
- Monitoring via CloudWatch.

## Dashboards
- Streamlit/FastAPI frontend for:
  - Live portfolio view.
  - Bucket allocations.
  - PnL and trade history.