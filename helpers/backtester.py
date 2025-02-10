import os
import pytz
import requests
import time
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from threading import Lock
from typing import List, Dict
from alpaca.trading.enums import OrderSide
from datetime import datetime
from helpers import logger
from helpers.strategies import bollinger_bands


class SlippageModel:

    def __init__(self, spread_bps=5, volatility_impact=True):
        self.spread_bps = spread_bps  # 0.05% default spread
        self.volatility_impact = volatility_impact

    def get_fill_price(self, bar: pd.Series, order_side: OrderSide, order_size: int):
        """
        bar: OHLCV data for current period
        order_side: 'buy' or 'sell'
        order_size: Number of shares/contracts
        """
        # Base price with spread impact
        spread = bar['close'] * (self.spread_bps / 10000)

        if order_side == OrderSide.BUY:
            base_price = bar['high'] + spread  # Worst case for buyer
        else:
            base_price = bar['low'] - spread   # Worst case for seller

        # Add volatility impact (using bar range)
        if self.volatility_impact:
            bar_range = bar['high'] - bar['low']
            volatility_impact = bar_range * 0.1 * np.random.randn()
            base_price += volatility_impact

        # Volume-adjusted impact (if volume data available)
        if 'volume' in bar:
            volume_impact = (order_size / bar['volume']) * bar_range
            base_price += volume_impact

        return np.clip(base_price, bar['low'], bar['high'])


class MockTradingStateManager:
    """Manages trading positions and P&L state for a strategy.

    Attributes:
        positions: Dictionary tracking current positions {symbol: {qty, entry_price}}
        lock: Thread lock for concurrent access to positions
        logger: Strategy-specific logger instance
        open_orders: Dictionary tracking working orders
        daily_pnl: Realized profit/loss for the current trading day
        market_close_buffer: Minutes before market close to initiate liquidation
    """
    def __init__(self, logger: logger.Logger, slippage: SlippageModel):
        """Initializes trading state manager for a specific strategy.

        Args:
            strategy_name: Identifier for strategy-specific logging
        """
        self.positions = {}  # { symbol: { 'qty': int, 'entry_price': float} }
        self.lock = Lock()
        self.logger = logger
        self.daily_pnl = 0.0
        self.slippage = slippage

    def update_position(self, symbol: str, qty: int, price: float) -> None:
        """Updates position for a symbol with thread-safe locking.

        Calculates new average price for additive positions and updates P&L
        for closed positions.

        Args:
            symbol: Trading symbol to update
            qty: Quantity to add/remove from position (positive for long, negative for short)
            price: Execution price for this transaction
        """
        with self.lock:
            current = self.positions.get(symbol, {'qty': 0, 'entry_price': 0.0})
            new_qty = current['qty'] + qty

            if new_qty == 0:
                self._update_pnl(symbol, current['entry_price'], price)
                del self.positions[symbol]
            else:
                total_value = (current['qty'] * current['entry_price']) + (qty * price)
                new_price = total_value / new_qty
                self.positions[symbol] = {
                    'qty': new_qty,
                    'entry_price': new_price,
                    'timestamp': datetime.now(pytz.utc)
                }

    def liquidate_all_positions(self) -> None:
        """Closes all positions via market orders and updates P&L.

        Iterates through all positions, submits market orders to close them,
        and handles any execution errors.
        """
        with self.lock:
            for symbol, position in self.positions.items():
                try:
                    filled_price = self.slippage.get_fill_price(
                        symbol=symbol,
                        qty=abs(position['qty']),
                        side=OrderSide.SELL if position['qty'] > 0 else OrderSide.BUY
                    )
                    self.update_position(symbol, -position['qty'], 0)
                    self._update_pnl(position['qty'], position['entry_price'], filled_price)
                except Exception as e:
                    self.logger.error(f'Failed to liquidate {symbol}: {e}')

    def _update_pnl(self, qty: int, entry_price: float, exit_price: float):
        """Updates daily realized P&L with closed position.

        Args:
            qty: Position quantity closed
            entry_price: Average entry price of position
            exit_price: Execution price for closing trade
        """
        self.daily_pnl += (exit_price - entry_price) * qty


class MockRiskManager:
    """Validates orders against risk parameters and current positions.

    Attributes:
        max_position_size: Maximum USD value per symbol position
        daily_loss_limit: Maximum allowed daily loss in USD
        state: Reference to associated TradingStateManager
    """

    def __init__(self, state_manager: MockTradingStateManager):
        """Initializes risk manager with strategy state.

        Args:
            state_manager: TradingStateManager instance for position data
        """
        self.max_position_size = 10000
        self.daily_loss_limit = -5000
        self.state = state_manager

    def validate_order(self, symbol: str, qty: int, price: float) -> bool:
        """Validates order against all risk checks.

        Args:
            symbol: Trading symbol for order
            qty: Proposed order quantity (positive for long, negative for short)
            price: Current market price for calculations

        Returns:
            bool: True if order passes all risk checks, False otherwise
        """
        if not self._is_market_open(datetime.now(pytz.utc)):
            self.state.logger.warning('Market closed - rejecting order')
            return False

        # prevents same direction trading
        if self._same_direction_trade(symbol, qty):
            return False

        if self._exceeds_position_size(symbol, qty, price):
            return False

        if self._exceeds_daily_loss_limit(qty, price):
            return False

        return True

    def _same_direction_trade(self, symbol: str, qty: int) -> bool:
        """
        Ensures that the directions of the trades happening are opposite
        """
        current_qty = self.state.positions.get(symbol, {}).get('qty', 0)
        if current_qty * qty > 0:  # Quick and easy way to tell if trade is on same side
            self.state.logger.warning(f'Existing {current_qty}, position conflicts with {qty} order')
            return True
        return False

    def _exceeds_daily_loss_limit(self, qty: int, price: float) -> bool:
        """
        Projects if order would exceed daily loss limit.
        Uses conservative 2% adverse move assumption for open positions.
        """
        projected_pnl = self._calculate_projected_pnl(qty, price)
        if (self.state.daily_pnl + projected_pnl) < self.daily_loss_limit:
            self.state.logger.warning(f"Daily loss limit exceeded: {self.state.daily_pnl + projected_pnl:.2f}")
            return True
        return False

    def _exceeds_position_size(self, symbol: str, qty: int, price: float) -> bool:
        """Checks if order exceeds maximum position size."""
        position = self.state.positions.get(symbol, {'qty': 0})
        new_notional = abs((position['qty'] + qty) * price)
        if new_notional > self.max_position_size:
            self.state.logger.warning(f'Position limit exceeded: {new_notional: .2f} / {self.max_position_size}')
            return True
        return False

    def _is_market_open(dt_utc: datetime) -> bool:
        """
        Check if UTC timestamp falls within NYSE market hours (9:30-16:00 ET)
        Simple version without holiday checks - assumes valid trading days
        """
        ny_tz = pytz.timezone('America/New_York')
        dt_ny = dt_utc.astimezone(ny_tz)

        # Check weekday (Mon-Fri)
        if dt_ny.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            return False

        # Check time within market hours
        open_time = time(9, 30)
        close_time = time(16, 0)
        current_time = dt_ny.time()

        return open_time <= current_time < close_time


class MockOrderExecutor:
    """Handles order execution with integrated risk checks.

    Attributes:
        state: TradingStateManager for position updates
        risk: RiskManager for order validation
    """

    def __init__(
        self,
        state_manager: MockTradingStateManager,
        risk_manager: MockRiskManager,
        slippage: SlippageModel
    ):
        """Initializes executor with state and risk components.

        Args:
            state_manager: TradingStateManager instance
            risk_manager: RiskManager instance
            strategy_universe: list of strategies known universe
        """
        self.state = state_manager
        self.risk = risk_manager
        self.slippage = slippage

    def execute_market_order(self, symbol: str, qty: int, current_price: float) -> bool:
        """Executes market order with full risk validation lifecycle.

        Args:
            symbol: Trading symbol for order
            qty: Order quantity (positive for long, negative for short)
            current_price: the current price of the asset, for mock trading,
                            this will be given by historical data
        Returns:
            bool: True if order executed successfully, False otherwise
        """
        try:
            if not current_price or not self.risk.validate_order(symbol, qty, current_price):
                return False

            filled_price = self.slippage.get_fill_price(
                symbo=symbol,
                order_side=OrderSide.BUY if qty > 0 else OrderSide.SEll,
                order_size=qty
            )
            self.state.update_position(
                symbol=symbol,
                qty=qty,
                price=filled_price
            )
            return True
        except Exception as e:
            self.state.logger.error(f'Execution market order failed {e}')
            return False

    def liquidate_all_positions(self) -> None:
        """Initiates complete position liquidation for the strategy."""
        try:
            self.state.liquidate_all_positions()
        except Exception as e:
            self.state.logger.error(f'Failed to liquidate all strategy positions: {e}')


class BackTester():
    def __init__(
        self,
        universe: list[str],
        initial_capital: float,
        order_exectuor: MockOrderExecutor,
        strategy: bollinger_bands.BollingerBands,
    ) -> None:
        self.capital = initial_capital
        self.universe = universe
        self.order_exectuor = order_exectuor
        self.strategy = strategy,

    def __fetch_historical_data(
        self,
        equity: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        try:
            res = requests.get(
                f"https://api.polygon.io/v2/aggs/ticker/{equity}/range/1/minute/{start_date}/{end_date}?apiKey={os.getenv('HISTORICAL_DATA_API_KEY')}"
            )
            logger.info(f"Successfully retrieved historical data for {equity}!")
            return res.text
        except Exception as e:
            logger.error(f"Error retrieving historical data {e}")

    def run(self) -> None:
        for symbol in self.universe:
            res = self.__fetch_historical_data(symbol, '2023-02-01', '2025-02-01')
        print(res)
        pass


if __name__ == '__main__':
    # Load in all envs
    load_dotenv()
    # Set up strategy to be tested
    backtest_strategy = bollinger_bands.BollingerBands(
        strategy_universe=['META']
    )
    # Generate a slippage model
    slippage_model = SlippageModel(
        spread_bps=5,
        volatility_impact=True
    )
    # Mock trading state manager with updates to portfolio
    trading_state_manager = MockTradingStateManager(
        slippage=slippage_model
    )
    # Mock risk manager
    risk_manager = MockRiskManager(
        state_manager=trading_state_manager
    )
    # Mock order executor
    order_executor = MockOrderExecutor()
    # Back testing framework
    backtester = BackTester(
        initial_capital=10000,
        universe=['META'],
        order_exectuor=order_executor,
        strategy=backtest_strategy
    )
    logger.info(f'Running backtest for {backtest_strategy.__name__}')
    # Run backtest
    backtester.run()
