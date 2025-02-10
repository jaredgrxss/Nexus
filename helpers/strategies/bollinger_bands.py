import pytz, time
from datetime import datetime, timedelta
from helpers import statistics
from alpaca.trading.enums import OrderSide
from alpaca.data.timeframe import TimeFrame


class BollingerBands:

    def __init__(self, strategy_universe: list[str]):
        self.strategy_universe = strategy_universe

    def generate_signal(self, message: dict):
        """
        Calculates a trading signal based on the provided market data message.

        This function analyzes the high, open, close, low, symbol, and timestamp from the input message
        to determine whether a trade should be executed. It currently prints the relevant market data
        and returns default values for the trade signal.

        Parameters:
        -----------
        message : dict
            A dictionary containing market data for a specific symbol. Expected keys are:
            - 'high' (float): The highest price of the symbol during the time period.
            - 'open' (float): The opening price of the symbol during the time period.
            - 'close' (float): The closing price of the symbol during the time period.
            - 'low' (float): The lowest price of the symbol during the time period.
            - 'symbol' (str): The trading symbol (e.g., 'TSLA').
            - 'timestamp' (str): The timestamp of the market data in ISO format.
        reversion_universe : str
            A universe related to this service
        Returns:
        --------
        tuple
            A tuple containing the following elements:
            - do (bool): A flag indicating whether to execute the trade. Default is False.
            - side (OrderSide): The side of the trade (BUY or SELL). Default is OrderSide.BUY.
            - qty (int): The quantity of the trade. Default is 1.
            - symbol (int): The trading symbol. Default is None

        Example:
        --------
        message = {
            'high': 383.89,
            'open': 383.495,
            'low': 383.49,
            'symbol': 'TSLA',
            'timestamp': '2025-02-03T19:36:00+00:00'
            'tradecount': 25
        }
        generate_signal(message)
        (False, OrderSide.BUY, 5, 'AAPL)
        """
        side = OrderSide.BUY
        qty = 0
        symbol = None
        do = False
        # ensure the symbol is in the strategy universe, will add SQS filter policy at a later date
        if message['symbol'] in self.strategy_universe:
            end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
            start_time = end_time - timedelta(hours=2)  # Ensure enough bars
            # IMPLEMENT FUNCTION TO GATHER LOOKBACK PERIOD OF DATA
            data = self.get_historical_bar_data(
                symbols=message['symbol'],
                start_date=start_time,
                end_date=end_time,
                timeframe=TimeFrame.Minute,
                limit=None
            )[message['symbol']]  # extract the symbol of concern

            close_prices = self.extract_close_data(data)
            bands = statistics.bollinger_bands(close_prices, 20)

            if message['close'] >= bands['upper_band'][-1]:
                do = True
                symbol = message['symbol']
                qty = -1
                side = OrderSide.SELL
            elif message['close'] <= bands['lower_band'][-1]:
                do = True
                symbol = message['symbol']
                qty = 1
                side = OrderSide.BUY
        return do, side, qty, symbol
    
    def less_than_fifteen(self, unix_bar_time: int) -> bool:
        """
        Check if there are 15 minutes or less left in the NYSE trading day.
        """
        ny_tz = pytz.timezone('America/New_York')
        dt_ny = dt_utc.astimezone(ny_tz)

        # Check if market is open
        if not _is_market_open(dt_utc):
            return False

        # Define market close time
        close_time_ny = datetime.combine(dt_ny.date(), time(16, 0)).astimezone(ny_tz)

        # Calculate time remaining
        time_remaining = close_time_ny - dt_ny

        # Check if 15 minutes or less remain
        return time_remaining <= timedelta(minutes=15)
        

    def get_historical_bar_data(self):
        pass

    def extract_close_data(self):
        pass
