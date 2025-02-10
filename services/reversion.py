import os
import time
import json
from datetime import datetime, timedelta
from helpers import cloud
from helpers import broker
from helpers import logger
from helpers import trading
from helpers import statistics
from alpaca.trading.enums import OrderSide
from alpaca.data.timeframe import TimeFrame

logger = logger.Logger('reversion.py')


def run() -> None:
    """
    A service for implementing a mean-reversion trading strategy by polling an SQS queue
    for trading signals and processing them. The first iteration of this strategy will
    be a long-only strategy.

    This function performs the following steps:
    1. Subscribes the reversion SQS queue to the data SNS topic to receive trading signals.
    2. Continuously polls the SQS queue for new messages (trading signals).
    3. Processes each message (e.g., executes trades or updates strategy state).
    4. Deletes processed messages from the SQS queue to avoid reprocessing.

    The service runs indefinitely, making it suitable for deployment as a long-running
    background process in an algorithmic trading platform.

    Environment Variables:
        - REVERSION_SQS_ARN: The ARN of the SQS queue used for the reversion strategy.
        - REVERSION_SQS_URL: The URL of the SQS queue used for the reversion strategy.
        - DATA_SNS: The ARN of the SNS topic that publishes trading data.
        - AWS_REGION: The AWS region where the SQS and SNS resources are located.
        - AWS_ACCESS_KEY_ID: The AWS access key for authentication.
        - AWS_SECRET_ACCESS_KEY: The AWS secret key for authentication.

    Raises:
        Logs errors if any of the following occur:
        - Failed to subscribe the SQS queue to the SNS topic.
        - Failed to poll messages from the SQS queue.
        - Failed to delete a processed message from the SQS queue.

    Notes:
        - This service is designed to be fault-tolerant. If an error occurs (e.g., failed
          to poll or delete a message), the service logs the error and continues running.
        - The service assumes that the SQS queue is configured to receive messages from
          the SNS topic and that the trading strategy logic is implemented elsewhere.
    """
    # Ensure the reversion SQS is subscribed to the data SNS
    try:
        cloud.subscribe_sqs_to_sns(
            queue_arn=os.getenv('REVERSION_SQS_ARN'),
            topic_arn=os.getenv('DATA_SNS')
        )
        logger.info('Successfully subscribed SQS to SNS.')
    except Exception as e:
        logger.error(f'Error subscribing to SNS data topic: {e}')
        return

    # Construct import strategy containers
    trading_state_manager = trading.TradingStateManager(logger=logger)
    risk_manager = trading.RiskManager(trading_state_manager)
    order_executor = trading.OrderExecutor(
        state_manager=trading_state_manager,
        risk_manager=risk_manager
        )

    # Get strategy universe
    reversion_universe = ['META']

    # Poll SQS for messages forever
    while True:
        try:
            # Poll messages from the SQS queue
            messages = cloud.poll_sqs_message(
                queue_url=os.getenv('REVERSION_SQS_URL')
            )
            if not messages:
                logger.info('No reversion queue messages available. Sleeping for 10 seconds...')
                time.sleep(10)
                continue
            # Process each message
            for message in messages:
                # Transform message for later use
                outer_message = json.loads(message['Body'])
                bar_data = json.loads(outer_message['Message'])
                logger.info(
                    f"Received SNS message: ID={message['MessageId']}, SYMBOL={bar_data['symbol']}"
                )
                # Delete the message from the queue after processing
                try:
                    cloud.delete_sqs_message(
                        queue_url=os.getenv('REVERSION_SQS_URL'),
                        receipt_handle=message['ReceiptHandle']
                    )
                except Exception as e:
                    logger.error(f'Error deleting SQS message: {e}')

                try:
                    # Don't generate signals if market is not open
                    if not broker.is_market_open() or broker.minutes_till_market_close() <= 15:
                        retry_minutes = broker.minutes_till_market_open() or 60
                        logger.info(
                            f'Market not open or <= 15 minutes left in trading day, skipping signal generation for {retry_minutes} minutes'
                        )
                        continue

                    # signal generation
                    do, side, qty, symbol = generate_signal(bar_data, reversion_universe)

                    # make sure signal said to move and that market is not about to close
                    if do and broker.minutes_till_market_close() > 15:
                        order_executor.execute_market_order(
                            symbol=symbol,
                            qty=qty if side == OrderSide.BUY else -qty
                        )

                    # Make sure to liquidate all positions 15 minutes prior to market close
                    if broker.minutes_till_market_close() <= 15:
                        order_executor.liquidate_all_positions()
                except Exception as e:
                    logger.error(f'Error in reversion strategy: {e}')
        except Exception as e:
            logger.error(f'Error receiving SQS message: {e}')


def generate_signal(message: dict, reversion_universe: list[str]):
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
    if message['symbol'] in reversion_universe:
        end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(hours=2)  # Ensure enough bars
        data = broker.get_historical_bar_data(
            symbols=message['symbol'],
            start_date=start_time,
            end_date=end_time,
            timeframe=TimeFrame.Minute,
            limit=None
        )[message['symbol']]  # extract the symbol of concern

        close_prices = broker.extract_close_data(data)
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
