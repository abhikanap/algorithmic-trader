-- PostgreSQL initialization script for Algorithmic Trading Platform
-- This script creates the necessary tables and indexes for the trading platform

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Set default schema
SET search_path TO trading, public;

-- ======================
-- TRADING TABLES
-- ======================

-- Stocks/Symbols reference table
CREATE TABLE IF NOT EXISTS symbols (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trading signals
CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL, -- 'buy', 'sell', 'hold'
    strategy VARCHAR(50) NOT NULL,
    confidence DECIMAL(3,2),
    price DECIMAL(10,2),
    quantity INTEGER,
    stop_loss DECIMAL(10,2),
    take_profit DECIMAL(10,2),
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID,
    external_order_id VARCHAR(100), -- Alpaca order ID
    symbol VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL, -- 'market', 'limit', 'stop'
    side VARCHAR(10) NOT NULL, -- 'buy', 'sell'
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2),
    stop_price DECIMAL(10,2),
    status VARCHAR(20) NOT NULL, -- 'pending', 'filled', 'cancelled', 'rejected'
    filled_quantity INTEGER DEFAULT 0,
    filled_price DECIMAL(10,2),
    commission DECIMAL(8,4),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    metadata JSONB,
    FOREIGN KEY (signal_id) REFERENCES signals(id),
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);

-- Positions
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    avg_price DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2),
    market_value DECIMAL(12,2),
    unrealized_pnl DECIMAL(12,2),
    realized_pnl DECIMAL(12,2),
    side VARCHAR(10) NOT NULL, -- 'long', 'short'
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);

-- Portfolio snapshots
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    total_value DECIMAL(15,2) NOT NULL,
    cash_balance DECIMAL(15,2) NOT NULL,
    equity_value DECIMAL(15,2) NOT NULL,
    daily_pnl DECIMAL(12,2),
    total_pnl DECIMAL(12,2),
    positions_count INTEGER,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- ======================
-- ANALYTICS TABLES
-- ======================

-- Backtesting results
CREATE TABLE IF NOT EXISTS analytics.backtest_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    backtest_id VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    final_capital DECIMAL(15,2) NOT NULL,
    total_return DECIMAL(8,4),
    annualized_return DECIMAL(8,4),
    sharpe_ratio DECIMAL(6,3),
    max_drawdown DECIMAL(8,4),
    win_rate DECIMAL(5,2),
    total_trades INTEGER,
    benchmark_symbol VARCHAR(10),
    benchmark_return DECIMAL(8,4),
    alpha DECIMAL(8,4),
    beta DECIMAL(6,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Performance metrics (daily)
CREATE TABLE IF NOT EXISTS analytics.daily_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,
    portfolio_value DECIMAL(15,2),
    daily_return DECIMAL(8,4),
    daily_pnl DECIMAL(12,2),
    volatility DECIMAL(8,4),
    sharpe_ratio DECIMAL(6,3),
    max_drawdown DECIMAL(8,4),
    positions_count INTEGER,
    trades_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ======================
-- MONITORING TABLES
-- ======================

-- System health metrics
CREATE TABLE IF NOT EXISTS monitoring.system_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4),
    metric_unit VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Application logs
CREATE TABLE IF NOT EXISTS monitoring.application_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL,
    logger VARCHAR(100),
    message TEXT NOT NULL,
    module VARCHAR(100),
    function VARCHAR(100),
    line_number INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- ======================
-- INDEXES
-- ======================

-- Trading indexes
CREATE INDEX IF NOT EXISTS idx_signals_symbol_created ON signals(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy);
CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON orders(symbol, status);
CREATE INDEX IF NOT EXISTS idx_orders_submitted_at ON orders(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_symbol_active ON positions(symbol, is_active);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_date ON portfolio_snapshots(snapshot_date DESC);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_backtest_results_backtest_id ON analytics.backtest_results(backtest_id);
CREATE INDEX IF NOT EXISTS idx_daily_performance_date ON analytics.daily_performance(date DESC);

-- Monitoring indexes
CREATE INDEX IF NOT EXISTS idx_system_health_timestamp ON monitoring.system_health(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_health_metric ON monitoring.system_health(metric_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_application_logs_timestamp ON monitoring.application_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_application_logs_level ON monitoring.application_logs(level, timestamp DESC);

-- ======================
-- FUNCTIONS
-- ======================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for symbols table
CREATE TRIGGER update_symbols_updated_at 
    BEFORE UPDATE ON symbols 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ======================
-- VIEWS
-- ======================

-- Active positions view
CREATE OR REPLACE VIEW active_positions AS
SELECT 
    p.*,
    s.name as symbol_name,
    s.sector,
    (p.current_price - p.avg_price) * p.quantity as unrealized_pnl_calc,
    (p.current_price - p.avg_price) / p.avg_price * 100 as unrealized_pnl_pct
FROM positions p
JOIN symbols s ON p.symbol = s.symbol
WHERE p.is_active = TRUE;

-- Portfolio summary view
CREATE OR REPLACE VIEW portfolio_summary AS
SELECT 
    COUNT(*) as total_positions,
    SUM(market_value) as total_market_value,
    SUM(unrealized_pnl) as total_unrealized_pnl,
    SUM(realized_pnl) as total_realized_pnl,
    AVG(unrealized_pnl / (avg_price * quantity) * 100) as avg_return_pct
FROM positions
WHERE is_active = TRUE;

-- Recent trades view
CREATE OR REPLACE VIEW recent_trades AS
SELECT 
    o.id,
    o.symbol,
    s.name as symbol_name,
    o.side,
    o.quantity,
    o.filled_price,
    o.commission,
    o.filled_quantity * o.filled_price as trade_value,
    o.filled_at,
    o.status
FROM orders o
JOIN symbols s ON o.symbol = s.symbol
WHERE o.status = 'filled'
ORDER BY o.filled_at DESC;

-- ======================
-- INITIAL DATA
-- ======================

-- Insert common symbols
INSERT INTO symbols (symbol, name, sector) VALUES
    ('AAPL', 'Apple Inc.', 'Technology'),
    ('GOOGL', 'Alphabet Inc.', 'Technology'),
    ('MSFT', 'Microsoft Corporation', 'Technology'),
    ('AMZN', 'Amazon.com Inc.', 'Consumer Discretionary'),
    ('TSLA', 'Tesla Inc.', 'Consumer Discretionary'),
    ('NVDA', 'NVIDIA Corporation', 'Technology'),
    ('META', 'Meta Platforms Inc.', 'Technology'),
    ('SPY', 'SPDR S&P 500 ETF Trust', 'ETF'),
    ('QQQ', 'Invesco QQQ Trust', 'ETF'),
    ('IWM', 'iShares Russell 2000 ETF', 'ETF')
ON CONFLICT (symbol) DO NOTHING;

-- ======================
-- PERMISSIONS
-- ======================

-- Grant permissions to trading user
GRANT USAGE ON SCHEMA trading TO trader;
GRANT USAGE ON SCHEMA analytics TO trader;
GRANT USAGE ON SCHEMA monitoring TO trader;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trading TO trader;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO trader;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA monitoring TO trader;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA trading TO trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA monitoring TO trader;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA trading GRANT ALL ON TABLES TO trader;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT ALL ON TABLES TO trader;
ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT ALL ON TABLES TO trader;

ALTER DEFAULT PRIVILEGES IN SCHEMA trading GRANT ALL ON SEQUENCES TO trader;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT ALL ON SEQUENCES TO trader;
ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT ALL ON SEQUENCES TO trader;

-- Create read-only user for reporting
CREATE USER reporter WITH PASSWORD 'reporting123';
GRANT USAGE ON SCHEMA trading TO reporter;
GRANT USAGE ON SCHEMA analytics TO reporter;
GRANT USAGE ON SCHEMA monitoring TO reporter;
GRANT SELECT ON ALL TABLES IN SCHEMA trading TO reporter;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO reporter;
GRANT SELECT ON ALL TABLES IN SCHEMA monitoring TO reporter;

COMMIT;
