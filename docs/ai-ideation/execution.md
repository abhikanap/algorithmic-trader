# Execution Flow

## Intraday Run
1. **Scheduler triggers job** (cron/K8s).
2. **Screener fetches candidates**.
3. **Analyzer classifies patterns**.
4. **Strategy Engine assigns to buckets**.
5. **Execution Engine submits trades** via Alpaca.
6. **Portfolio Engine rebalances** (if thresholds breached).
7. **Logs written** to S3 + RDS.

## Order Handling
- All trades routed via Alpaca REST API.
- Orders tagged with `bucket_id`, `pattern_id`, `timeslot`.
- Risk mgmt:
  - Max 2% capital per trade.
  - Stop-loss: 1.5x ATR.
  - Take-profit: 2–3x ATR.
  - Trailing stops enabled.

## Portfolio Balancing
- At each intraday timeslot, reallocate if:
  - bucket overweight > target + threshold.
  - realized volatility changes.