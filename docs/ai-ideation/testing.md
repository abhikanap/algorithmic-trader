# Testing Plan

## Unit Tests
- Indicators (ATR, RSI, MACD, Bollinger).
- Pattern classifiers (mock OHLCV).
- Alpaca API wrapper (mock responses).

## Integration Tests
- End-to-end screener → analyzer → strategy → execution (sandbox mode).
- Alpaca paper trading account.

## Backtesting
- QuantConnect Lean:
  - Replay intraday data.
  - Validate strategy mapping.
- Metrics:
  - Win rate, PnL, Sharpe ratio.
  - Bucket-level performance.

## Walk-Forward Tests
- Run strategies on rolling windows.
- Compare vs baseline SMA/RSI strategies.