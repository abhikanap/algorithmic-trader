"""Trading simulator for backtesting."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from packages.core import get_logger


class TradingSimulator:
    """Simulates trading execution for backtesting."""
    
    def __init__(
        self,
        commission_per_trade: float = 1.00,
        slippage_bps: float = 2.0,
        max_position_size: float = 10000.0,
        max_positions: int = 20
    ):
        self.logger = get_logger(__name__)
        
        # Trading costs and constraints
        self.commission_per_trade = commission_per_trade
        self.slippage_bps = slippage_bps / 10000  # Convert basis points to decimal
        self.max_position_size = max_position_size
        self.max_positions = max_positions
        
        self.logger.info(f"Initialized simulator: commission=${commission_per_trade}, slippage={slippage_bps}bps")
    
    async def simulate_trades(
        self,
        signals_df: pd.DataFrame,
        market_data: pd.DataFrame,
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Simulate trade execution.
        
        Args:
            signals_df: DataFrame with trade signals
            market_data: Historical market data
            initial_capital: Starting capital
            
        Returns:
            Simulation results with trades and equity curve
        """
        self.logger.info(f"Starting simulation with ${initial_capital:,.2f}")
        
        if signals_df.empty:
            self.logger.warning("No signals to simulate")
            return self._empty_result(initial_capital)
        
        # Initialize simulation state
        portfolio = {
            "cash": initial_capital,
            "equity": initial_capital,
            "positions": {},  # symbol -> position info
            "open_orders": [],
            "filled_trades": []
        }
        
        equity_curve = []
        
        # Sort signals and market data by date
        signals_df = signals_df.sort_values('signal_date').reset_index(drop=True)
        market_data = market_data.sort_values(['date', 'symbol']).reset_index(drop=True)
        
        # Create market data lookup
        market_lookup = self._create_market_lookup(market_data)
        
        # Get unique trading dates
        trading_dates = sorted(signals_df['signal_date'].unique())
        
        self.logger.info(f"Simulating {len(trading_dates)} trading days")
        
        for date in trading_dates:
            self.logger.debug(f"Processing {date}")
            
            # Process new signals for this date
            daily_signals = signals_df[signals_df['signal_date'] == date]
            self._process_new_signals(daily_signals, portfolio, market_lookup, date)
            
            # Update existing positions with market data
            self._update_positions(portfolio, market_lookup, date)
            
            # Check for position exits (stops, targets, time-based)
            self._check_position_exits(portfolio, market_lookup, date)
            
            # Calculate portfolio equity
            equity = self._calculate_equity(portfolio, market_lookup, date)
            
            equity_curve.append({
                "date": date,
                "cash": portfolio["cash"],
                "equity": equity,
                "num_positions": len(portfolio["positions"])
            })
            
            portfolio["equity"] = equity
        
        # Close any remaining positions
        final_date = max(trading_dates) if trading_dates else datetime.now().strftime('%Y-%m-%d')
        self._close_all_positions(portfolio, market_lookup, final_date)
        
        # Prepare results
        trades_df = pd.DataFrame(portfolio["filled_trades"])
        equity_df = pd.DataFrame(equity_curve)
        
        result = {
            "trades": portfolio["filled_trades"],
            "trades_df": trades_df,
            "equity_curve": equity_df,
            "final_equity": portfolio["equity"],
            "final_cash": portfolio["cash"],
            "positions_closed": len(portfolio["filled_trades"]),
            "positions_open": len(portfolio["positions"])
        }
        
        self.logger.info(
            f"Simulation complete: {len(trades_df)} trades, "
            f"Final equity: ${portfolio['equity']:,.2f}"
        )
        
        return result
    
    def _empty_result(self, initial_capital: float) -> Dict[str, Any]:
        """Return empty simulation result."""
        return {
            "trades": [],
            "trades_df": pd.DataFrame(),
            "equity_curve": pd.DataFrame([{
                "date": datetime.now().strftime('%Y-%m-%d'),
                "cash": initial_capital,
                "equity": initial_capital,
                "num_positions": 0
            }]),
            "final_equity": initial_capital,
            "final_cash": initial_capital,
            "positions_closed": 0,
            "positions_open": 0
        }
    
    def _create_market_lookup(self, market_data: pd.DataFrame) -> Dict[str, Dict[str, pd.Series]]:
        """Create efficient market data lookup."""
        
        lookup = {}
        
        for symbol in market_data['symbol'].unique():
            symbol_data = market_data[market_data['symbol'] == symbol].copy()
            symbol_data = symbol_data.set_index('date')
            
            lookup[symbol] = {
                'open': symbol_data['open'],
                'high': symbol_data['high'],
                'low': symbol_data['low'],
                'close': symbol_data['close'],
                'volume': symbol_data['volume']
            }
        
        return lookup
    
    def _process_new_signals(
        self,
        signals: pd.DataFrame,
        portfolio: Dict[str, Any],
        market_lookup: Dict[str, Dict[str, pd.Series]],
        date: str
    ):
        """Process new trading signals."""
        
        for _, signal in signals.iterrows():
            symbol = signal['symbol']
            
            # Skip if already have position in this symbol
            if symbol in portfolio["positions"]:
                continue
            
            # Skip if we're at max positions
            if len(portfolio["positions"]) >= self.max_positions:
                continue
            
            # Get market data for entry
            if symbol not in market_lookup:
                continue
            
            if date not in market_lookup[symbol]['open'].index:
                continue
            
            # Calculate entry price with slippage
            entry_price = self._calculate_entry_price(signal, market_lookup[symbol], date)
            
            if entry_price <= 0:
                continue
            
            # Calculate position size
            position_size = min(signal.get('position_size', self.max_position_size), self.max_position_size)
            shares = int(position_size / entry_price)
            
            if shares <= 0:
                continue
            
            # Check if we have enough cash
            total_cost = shares * entry_price + self.commission_per_trade
            
            if total_cost > portfolio["cash"]:
                # Scale down position to available cash
                available_cash = portfolio["cash"] - self.commission_per_trade
                if available_cash > 0:
                    shares = int(available_cash / entry_price)
                    total_cost = shares * entry_price + self.commission_per_trade
                else:
                    continue
            
            if shares <= 0:
                continue
            
            # Create position
            position = {
                "symbol": symbol,
                "signal_type": signal.get('signal_type', 'LONG'),
                "shares": shares,
                "entry_price": entry_price,
                "entry_date": date,
                "stop_loss_price": signal.get('stop_loss_price', 0),
                "target_price": signal.get('target_price', 0),
                "pattern": signal.get('pattern_intraday', 'UNKNOWN'),
                "bucket": signal.get('bucket', 'UNKNOWN'),
                "current_price": entry_price,
                "unrealized_pnl": 0,
                "max_profit": 0,
                "max_loss": 0
            }
            
            # Add position to portfolio
            portfolio["positions"][symbol] = position
            portfolio["cash"] -= total_cost
            
            self.logger.debug(f"Opened {signal.get('signal_type', 'LONG')} position: {symbol} @ ${entry_price:.2f}")
    
    def _calculate_entry_price(
        self,
        signal: pd.Series,
        symbol_data: Dict[str, pd.Series],
        date: str
    ) -> float:
        """Calculate entry price with slippage."""
        
        if date not in symbol_data['open'].index:
            return 0
        
        # Use opening price as base
        base_price = symbol_data['open'][date]
        
        # Apply slippage based on signal type
        signal_type = signal.get('signal_type', 'LONG')
        
        if signal_type == 'LONG':
            # Long positions pay the ask (higher price)
            entry_price = base_price * (1 + self.slippage_bps)
        else:
            # Short positions receive the bid (lower price)
            entry_price = base_price * (1 - self.slippage_bps)
        
        return round(entry_price, 2)
    
    def _update_positions(
        self,
        portfolio: Dict[str, Any],
        market_lookup: Dict[str, Dict[str, pd.Series]],
        date: str
    ):
        """Update existing positions with current market data."""
        
        for symbol, position in portfolio["positions"].items():
            if symbol not in market_lookup or date not in market_lookup[symbol]['close'].index:
                continue
            
            current_price = market_lookup[symbol]['close'][date]
            position["current_price"] = current_price
            
            # Calculate unrealized P&L
            if position["signal_type"] == "LONG":
                pnl = (current_price - position["entry_price"]) * position["shares"]
            else:  # SHORT
                pnl = (position["entry_price"] - current_price) * position["shares"]
            
            position["unrealized_pnl"] = pnl - self.commission_per_trade
            
            # Track max profit/loss
            position["max_profit"] = max(position["max_profit"], pnl)
            position["max_loss"] = min(position["max_loss"], pnl)
    
    def _check_position_exits(
        self,
        portfolio: Dict[str, Any],
        market_lookup: Dict[str, Dict[str, pd.Series]],
        date: str
    ):
        """Check if any positions should be closed."""
        
        positions_to_close = []
        
        for symbol, position in portfolio["positions"].items():
            if symbol not in market_lookup or date not in market_lookup[symbol].get('high', pd.Series()).index:
                continue
            
            # Get intraday prices
            high = market_lookup[symbol]['high'][date]
            low = market_lookup[symbol]['low'][date]
            close = market_lookup[symbol]['close'][date]
            
            exit_price = None
            exit_reason = None
            
            # Check stops and targets based on intraday prices
            if position["signal_type"] == "LONG":
                # Check stop loss
                if position["stop_loss_price"] > 0 and low <= position["stop_loss_price"]:
                    exit_price = position["stop_loss_price"]
                    exit_reason = "STOP_LOSS"
                
                # Check target (only if not stopped out)
                elif position["target_price"] > 0 and high >= position["target_price"]:
                    exit_price = position["target_price"]
                    exit_reason = "TARGET"
            
            else:  # SHORT
                # Check stop loss
                if position["stop_loss_price"] > 0 and high >= position["stop_loss_price"]:
                    exit_price = position["stop_loss_price"]
                    exit_reason = "STOP_LOSS"
                
                # Check target (only if not stopped out)
                elif position["target_price"] > 0 and low <= position["target_price"]:
                    exit_price = position["target_price"]
                    exit_reason = "TARGET"
            
            # Check time-based exit (hold for max 5 days)
            entry_date = datetime.strptime(position["entry_date"], '%Y-%m-%d')
            current_date = datetime.strptime(date, '%Y-%m-%d')
            
            if (current_date - entry_date).days >= 5 and exit_price is None:
                exit_price = close
                exit_reason = "TIME_EXIT"
            
            # Close position if exit condition met
            if exit_price is not None:
                self._close_position(portfolio, symbol, exit_price, exit_reason, date)
                positions_to_close.append(symbol)
        
        # Remove closed positions
        for symbol in positions_to_close:
            del portfolio["positions"][symbol]
    
    def _close_position(
        self,
        portfolio: Dict[str, Any],
        symbol: str,
        exit_price: float,
        exit_reason: str,
        exit_date: str
    ):
        """Close a position and record the trade."""
        
        position = portfolio["positions"][symbol]
        
        # Apply slippage to exit price
        if position["signal_type"] == "LONG":
            # Selling at bid (lower price)
            actual_exit_price = exit_price * (1 - self.slippage_bps)
        else:
            # Covering at ask (higher price)
            actual_exit_price = exit_price * (1 + self.slippage_bps)
        
        actual_exit_price = round(actual_exit_price, 2)
        
        # Calculate P&L
        if position["signal_type"] == "LONG":
            gross_pnl = (actual_exit_price - position["entry_price"]) * position["shares"]
        else:
            gross_pnl = (position["entry_price"] - actual_exit_price) * position["shares"]
        
        net_pnl = gross_pnl - (2 * self.commission_per_trade)  # Entry + exit commissions
        
        # Calculate metrics
        entry_date = datetime.strptime(position["entry_date"], '%Y-%m-%d')
        exit_date_dt = datetime.strptime(exit_date, '%Y-%m-%d')
        hold_time = (exit_date_dt - entry_date).days
        
        # Record trade
        trade = {
            "symbol": symbol,
            "signal_type": position["signal_type"],
            "pattern": position["pattern"],
            "bucket": position["bucket"],
            "shares": position["shares"],
            "entry_date": position["entry_date"],
            "entry_price": position["entry_price"],
            "exit_date": exit_date,
            "exit_price": actual_exit_price,
            "exit_reason": exit_reason,
            "gross_pnl": gross_pnl,
            "pnl": net_pnl,
            "return_pct": (net_pnl / (position["entry_price"] * position["shares"])) * 100,
            "hold_time_days": hold_time,
            "hold_time_hours": hold_time * 24,
            "max_profit": position["max_profit"],
            "max_loss": position["max_loss"]
        }
        
        portfolio["filled_trades"].append(trade)
        
        # Update cash
        proceeds = position["shares"] * actual_exit_price - self.commission_per_trade
        portfolio["cash"] += proceeds
        
        self.logger.debug(
            f"Closed {position['signal_type']} {symbol}: ${net_pnl:.2f} "
            f"({exit_reason}, {hold_time}d)"
        )
    
    def _close_all_positions(
        self,
        portfolio: Dict[str, Any],
        market_lookup: Dict[str, Dict[str, pd.Series]],
        final_date: str
    ):
        """Close all remaining positions at market close."""
        
        symbols_to_close = list(portfolio["positions"].keys())
        
        for symbol in symbols_to_close:
            if symbol in market_lookup and final_date in market_lookup[symbol]['close'].index:
                close_price = market_lookup[symbol]['close'][final_date]
                self._close_position(portfolio, symbol, close_price, "FINAL_CLOSE", final_date)
            
            del portfolio["positions"][symbol]
    
    def _calculate_equity(
        self,
        portfolio: Dict[str, Any],
        market_lookup: Dict[str, Dict[str, pd.Series]],
        date: str
    ) -> float:
        """Calculate total portfolio equity."""
        
        equity = portfolio["cash"]
        
        # Add value of open positions
        for symbol, position in portfolio["positions"].items():
            if symbol in market_lookup and date in market_lookup[symbol]['close'].index:
                current_price = market_lookup[symbol]['close'][date]
                position_value = position["shares"] * current_price
                equity += position_value
        
        return round(equity, 2)
