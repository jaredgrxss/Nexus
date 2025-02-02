import os
import time
import signal
import json
import asyncio
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar
from helpers import logger, broker, cloud

# Configure logger
logger = logger.Logger('data.py')

# Initialize placeholders for the stream client and universe
broker_stream_client = None
broker_universe = None


def get_broker_stream_client():
    """
    Lazily initializes and returns the StockDataStream client.
    Ensures environment variables are loaded before creating the client.
    """
    api_key = os.getenv('BROKER_API_KEY')
    api_secret = os.getenv('BROKER_SECRET_KEY')
    universe = os.getenv('UNIVERSE').split(',')
    if not api_key or not api_secret:
        raise ValueError("Broker API credentials are missing in environment variables.")

    stream_client = StockDataStream(api_key, api_secret)
    return stream_client, universe


def get_broker_stream():
    """
    Returns the StockDataStream client and universe.
    Initializes the client and universe if they haven't been initialized yet.
    """
    global broker_stream_client, broker_universe
    if broker_stream_client is None or broker_universe is None:
        broker_stream_client, broker_universe = get_broker_stream_client()
    return broker_stream_client, broker_universe


def run() -> None:
    """
    Main function to run the data service.

    This function continuously checks if the market is open.
    If the market is open, it establishes a WebSocket connection to stream
    real-time bar data for the specified universe of stocks.
    The service handles graceful shutdown on receiving termination
    signals (e.g., SIGINT or SIGTERM) and retries in case of errors.

    The service performs the following steps:
    1. Checks if the market is open.
    2. If the market is open, connects to the Alpaca WebSocket stream.
    3. Subscribes to bar data for the specified universe of stocks.
    4. Handles incoming bar data using the `bar_handler` function.
    5. Monitors for termination signals to shut down gracefully.
    6. Retries the connection in case of errors.

    Environment Variables:
        BROKER_API_KEY (str): Alpaca API key.
        BROKER_SECRET_KEY (str): Alpaca API secret key.
        UNIVERSE (str): Comma-separated list of stock symbols to subscribe to.
    """
    stream_client, universe = get_broker_stream_client()
    shutdown = False

    def handle_single(signum, frame):
        nonlocal shutdown
        logger.info(f'Received shutdown signal {signum}')
        shutdown = True
        stream_client.stop()

    signal.signal(signal.SIGINT, handle_single)
    signal.signal(signal.SIGTERM, handle_single)

    while not shutdown:
        try:
            # Check if the market is open
            if not broker.is_market_open():
                retry_minutes = broker.minutes_till_market_open() or 60
                logger.info(f'Market closed. Sleeping {retry_minutes} minutes')
                time.sleep(retry_minutes * 60)
                continue

            logger.info("Adding universe to stream.")

            # Unpack and subscribe universe
            stream_client.subscribe_bars(bar_handler, *universe)

            # Start the websocket connection
            logger.info("Starting market data stream.")
            stream_client.run()
        except Exception as e:
            logger.error(f"Error in data service: {e}")
            if not shutdown:
                logger.info("Retrying in 1 minutes...")
                time.sleep(60)


async def bar_handler(bar: Bar):
    """
    Handles incoming bar data for subscribed symbols.

    Args:
        bar (Bar): The bar data object containing information
                   like symbol, timestamp,
                   open, high, low, close, and volume.
    """
    try:
        # Convert bar object to SNS format
        message = {
            'symbol': bar.symbol,
            'timestamp': bar.timestamp.isoformat(),
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume,
            'trade_count': bar.trade_count
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            cloud.publish_sns_message,
            json.dumps(message),
            os.getenv('DATA_SNS')
        )
    except Exception as e:
        logger.error(f'Error in publishing bar data to data topic {e}')


def dummy_test() -> int:
    return 1
