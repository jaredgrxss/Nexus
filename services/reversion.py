import os
from helpers import cloud, logger

logger = logger.Logger('reversion.py')


def run() -> None:
    """
    A service for implementing a mean-reversion trading strategy by polling an SQS queue
    for trading signals and processing them.

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

    # Poll SQS for messages forever
    while True:
        try:
            # Poll messages from the SQS queue
            messages = cloud.poll_sqs_message(
                queue_url=os.getenv('REVERSION_SQS_URL')
            )

            if not messages:
                logger.info('No reversion queue messages received.')
                continue

            # Process each message
            for message in messages:
                logger.info(
                    f"Received SNS message: ID={message['MessageId']}, Body={message['Body']}"
                )

                # Delete the message from the queue after processing
                try:
                    cloud.delete_sqs_message(
                        queue_url=os.getenv('REVERSION_SQS_URL'),
                        receipt_handle=message['ReceiptHandle']
                    )
                except Exception as e:
                    logger.error(f'Error deleting SQS message: {e}')
        except Exception as e:
            logger.error(f'Error receiving SQS message: {e}')
