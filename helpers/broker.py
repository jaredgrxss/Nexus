import os
from logger import Logger
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data import StockhistoricalDataClient 
from alpaca.data.requests import StockBarsRequest, StockQuotesRequest, StockTradesRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
from typing import Optional, List

# Initialize logger
logger = Logger('broker.py')

# Intialize clients for reuse
trading_client = TradingClient(
    os.environ.get('BROKER_API_KEY'), 
    os.environ.get('BROKER_SECRET_KEY'),
    paper=False if os.environ.get('ENV') == 'production' else True
)
stock_client = StockhistoricalDataClient(
    os.environ.get('ALPACA_API_KEY'), 
    os.environ.get('ALPACA_SECRET_KEY')
)

def is_market_open() -> bool:
    """
    Check if the stock market is currently open.

    Returns:
        bool: True if the market is open, False otherwise.
    """
    try:
        # Get the market clock 
        clock = trading_client.get_clock()
        return clock.is_open
    except Exception as e:
        raise Exception(f"Failed to check market status: {e}") from e
        
def minutes_till_market_close() -> int:
    """
    Calculate the number of minutes remaining until the stock market closes.

    Returns:
        int: The number of minutes until the market closes. Returns 0 if the market is closed.
    """
    try: 
        # Get the market clock
        clock = trading_client.get_clock()
        
        # Check if the market is open 
        if not clock.is_open:
            return 0
        
        # Caclulate the time difference between now and the next market close 
        now = clock.timestamp
        next_close = clock.next_close
        time_difference = next_close - now 
        
        # Conver the time difference to minutes
        minutes_remaining = int(time_difference.total_seconds() / 60)
        return minutes_remaining
    except Exception as e:
        raise Exception(f"Failed to calculate minutes until market close: {e}") from e

def place_market_order(
    symbol: str, 
    qty: float, 
    side: OrderSide, 
    time_in_force: TimeInForce = TimeInForce.DAY
) -> None:
    """
    Place a market order.

    Args:
        symbol (str): The stock symbol to trade (e.g., "AAPL").
        qty (float): The quantity of shares to trade.
        side (OrderSide): The side of the order (e.g., OrderSide.BUY or OrderSide.SELL).
        time_in_force (TimeInForce, optional): The time-in-force for the order (e.g., TimeInForce.DAY).
                                              Defaults to TimeInForce.DAY.

    Raises:
        Exception: If the order placement fails.
    """
    try:
        # Create a market order request
        market_order = MarketOrderRequest(
            symbol='AAPL',
            qty=1,
            side=OrderSide.BUY,
            time_in_force=time_in_force
        )
        
        # Place the market order
        trading_client.submit_order(market_order)
        logger.info(f"Market order placed for {qty} shares of {symbol} ({side.value})")
    except Exception as e:
        raise Exception(f"Failed to place market order: {e}") from e

def place_limit_order(
    symbol: str,
    qty: float,
    side: OrderSide,
    limit_price: float, 
    time_in_force: TimeInForce = TimeInForce.DAY
) -> None:
    """
    Place a limit order.

    Args:
        symbol (str): The stock symbol to trade (e.g., "AAPL").
        qty (float): The quantity of shares to trade.
        side (OrderSide): The side of the order (e.g., OrderSide.BUY or OrderSide.SELL).
        limit_price (float): The limit price for the order.
        time_in_force (TimeInForce, optional): The time-in-force for the order (e.g., TimeInForce.DAY).
                                              Defaults to TimeInForce.DAY.

    Raises:
        Exception: If the order placement fails.
    """
    try:
        # Create a limit order request 
        limit_order = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side,
            limit_price=limit_price,
            time_in_force=time_in_force
        )
        
        # Place the order 
        trading_client.submit_order(limit_order)
        logger.info(f"Limit order placed for {qty} shares of {symbol} ({side.value}) at ${limit_price}")
    except Exception as e:
        raise Exception(f"Failed to place limit order: {e}") from e

def get_historical_bar_data(
    symbols: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    timeframe: TimeFrame = TimeFrame.Hour,
    limit: Optional[int] = None
) -> dict:
    """
    Retrieve historical bar data for a list of stock symbols.

    Args:
        symbols (List[str]): A list of stock symbols (e.g., ["AAPL", "MSFT"]).
        start_date (datetime): The start date for the historical data.
        end_date (datetime): The end date for the historical data.
        timeframe (TimeFrame, optional): The granularity of the data (e.g., TimeFrame.Day, TimeFrame.Minute).
                                         Defaults to TimeFrame.Day.
        limit (Optional[int], optional): The maximum number of data points to retrieve. Defaults to None.

    Returns:
        dict: A dictionary containing historical bar data for the specified symbols.
    """
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=timeframe,
        start=start_date,
        end=end_date,
        limit=limit
    )
    bars = stock_client.get_bars(request)
    return bars.df # Returns a pandas dataframe     

def get_historical_quote_data(
    symbols: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    limit: Optional[int] = None
) -> dict:
    """
    Retrieve historical quote data for a list of stock symbols.

    Args:
        symbols (List[str]): A list of stock symbols (e.g., ["AAPL", "MSFT"]).
        start_date (datetime): The start date for the historical data.
        end_date (datetime): The end date for the historical data.
        limit (Optional[int], optional): The maximum number of data points to retrieve. Defaults to None.

    Returns:
        dict: A dictionary containing historical quote data for the specified symbols.
    """
    request = StockQuotesRequest(
        symbol_or_symbols=symbols,
        start=start_date,
        end=end_date,
        limit=limit
    )
    quotes = stock_client.get_quotes(request)
    return quotes.df # Returns a pandas dataframe

def get_historical_trade_data(
    symbols: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    limit: Optional[int] = None
) -> dict:
    """
    Retrieve historical trade data for a list of stock symbols.

    Args:
        symbols (List[str]): A list of stock symbols (e.g., ["AAPL", "MSFT"]).
        start_date (datetime): The start date for the historical data.
        end_date (datetime): The end date for the historical data.
        limit (Optional[int], optional): The maximum number of data points to retrieve. Defaults to None.

    Returns:
        dict: A dictionary containing historical trade data for the specified symbols.
    """
    request = StockTradesRequest(
        symbol_or_symbols=symbols,
        start=start_date,
        end=end_date,
        limit=limit
    )
    trades = stock_client.get_trades(request)
    return trades.df # Returns a pandas dataframe
