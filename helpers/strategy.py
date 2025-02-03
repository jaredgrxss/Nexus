import pytz
from datetime import datetime, timedelta
from alpaca.trading.enums import OrderSide, TimeInForce
from . import broker, logger
from threading import Lock
from typing import Optional


class TradingStateManager:
    """Manages trading positions and P&L state for a strategy.

    Attributes:
        positions: Dictionary tracking current positions {symbol: {qty, entry_price}}
        lock: Thread lock for concurrent access to positions
        logger: Strategy-specific logger instance
        open_orders: Dictionary tracking working orders
        daily_pnl: Realized profit/loss for the current trading day
        market_close_buffer: Minutes before market close to initiate liquidation
    """
    def __init__(self, logger: logger.Logger):
        """Initializes trading state manager for a specific strategy.

        Args:
            strategy_name: Identifier for strategy-specific logging
        """
        self.positions = {}  # { symbol: { 'qty': int, 'entry_price': float} }
        self.lock = Lock()
        self.logger = logger
        self.daily_pnl = 0.0

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
                    filled_price = broker.place_market_order(
                            symbol=symbol,
                            qty=abs(position['qty']),
                            side=OrderSide.SELL if position['qty'] > 0 else OrderSide.BUY,
                            time_in_force=TimeInForce.DAY
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


class RiskManager:
    """Validates orders against risk parameters and current positions.

    Attributes:
        max_position_size: Maximum USD value per symbol position
        daily_loss_limit: Maximum allowed daily loss in USD
        state: Reference to associated TradingStateManager
    """

    def __init__(self, state_manager: TradingStateManager):
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
        if not broker.is_market_open():
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


class OrderExecutor:
    """Handles order execution with integrated risk checks.

    Attributes:
        state: TradingStateManager for position updates
        risk: RiskManager for order validation
    """

    def __init__(self, state_manager: TradingStateManager, risk_manager: RiskManager):
        """Initializes executor with state and risk components.

        Args:
            state_manager: TradingStateManager instance
            risk_manager: RiskManager instance
            strategy_universe: list of strategies known universe
        """
        self.state = state_manager
        self.risk = risk_manager

    def execute_market_order(self, symbol: str, qty: int) -> bool:
        """Executes market order with full risk validation lifecycle.

        Args:
            symbol: Trading symbol for order
            qty: Order quantity (positive for long, negative for short)

        Returns:
            bool: True if order executed successfully, False otherwise
        """
        try:
            current_price = self._get_current_price(symbol)
            if not current_price or not self.risk.validate_order(symbol, qty, current_price):
                return False

            filled_price = broker.place_market_order(
                symbol=symbol,
                qty=abs(qty),
                side=OrderSide.BUY if qty > 0 else OrderSide.SELL,
                time_in_force=TimeInForce.DAY
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

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """
            Retreives the latest price of an asset
        """
        try:
            current_price = broker.get_historical_trade_data(
                symbols=[symbol],
                start_date=pytz.utc() - timedelta(seconds=30),
                end_date=pytz.utc(),
                limit=1
            )[symbol].iloc[-1]['price']
            return current_price
        except Exception as e:
            self.state.logger.error(f'Error in retreiving current price of {symbol}: {e}')
            return None

    def liquidate_all_positions(self) -> None:
        """Initiates complete position liquidation for the strategy."""
        try:
            self.state.liquidate_all_positions()
        except Exception as e:
            self.state.logger.error(f'Failed to liquidate all strategy positions: {e}')
