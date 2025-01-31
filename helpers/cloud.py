import boto3, json, os, gnupg
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

# Initialize AWS clients with a session for better resource management
session = boto3.Session(
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION', 'us-east-1') # Default to us-east-1 if not specified
)
sns_client = session.client('sns')
sqs_client = session.client('sqs')
secretsmanager_client = session.client('secretsmanager')

def publish_sns_message(data: str, topic: str) -> dict:
    """
    Publish a message to an SNS topic.

    Args:
        data (str): The message data to publish.
        topic (str): The ARN of the SNS topic.

    Returns:
        dict: The response from the SNS service.

    Raises:
        NoCredentialsError: If AWS credentials are not found.
        PartialCredentialsError: If AWS credentials are incomplete.
        ClientError: If there is an error publishing the message.
    """
    try:
        response = sns_client.publish(
            TopicArn=topic,
            Message=data,
        ) 
        return response
    except (NoCredentialsError, PartialCredentialsError) as e:
        raise Exception('AWS credentials are missing or incomplete.') from e
    except ClientError as e:
        raise Exception(f"Failed to publish message to SNS topic: {e}") from e

def poll_sqs_message(queue_url: str, max_messages: int = 1, wait_time_seconds: int = 10) -> list:
    """
    Poll messages from an SQS queue.

    Args:
        queue_url (str): The URL of the SQS queue.
        max_messages (int, optional): The maximum number of messages to retrieve. Defaults to 1.
        wait_time_seconds (int, optional): The duration (in seconds) to wait for messages. Defaults to 10.

    Returns:
        list: A list of messages retrieved from the queue.

    Raises:
        NoCredentialsError: If AWS credentials are not found.
        PartialCredentialsError: If AWS credentials are incomplete.
        ClientError: If there is an error polling messages.
    """
    try:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time_seconds,
        )
        return response.get('Messages', [])
    except (NoCredentialsError, PartialCredentialsError) as e:
        raise Exception('AWS credentials are missing or incomplete.') from e
    except ClientError as e:
        raise Exception(f"Failed to poll messages from SQS queue: {e}") from e

def delete_sqs_message(queue_url: str, receipt_handle: str) -> None:
    """
    Delete a message from an SQS queue.

    Args:
        queue_url (str): The URL of the SQS queue.
        receipt_handle (str): The receipt handle of the message to delete.

    Raises:
        NoCredentialsError: If AWS credentials are not found.
        PartialCredentialsError: If AWS credentials are incomplete.
        ClientError: If there is an error deleting the message.
    """ 
    try: 
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle,
        )
    except (NoCredentialsError, PartialCredentialsError) as e:
        raise Exception('AWS credentials are missing or incomplete.') from e
    except ClientError as e:
        raise Exception(f"Failed to delete message from SQS queue: {e}") from e

def subscribe_sqs_to_sns(queue_arn: str, topic_arn: str) -> dict:
    """
    Subscribe an SQS queue to an SNS topic.

    Args:
        queue_arn (str): The ARN of the SQS queue.
        topic_arn (str): The ARN of the SNS topic.

    Returns:
        dict: The response from the SNS service.

    Raises:
        NoCredentialsError: If AWS credentials are not found.
        PartialCredentialsError: If AWS credentials are incomplete.
        ClientError: If there is an error subscribing the queue to the topic.
    """
    try:
        response = sns_client.subscribe(
            Protocol='sqs',
            TopicArn=topic_arn,
            Endpoint=queue_arn,
        )
        return response
    except (NoCredentialsError, PartialCredentialsError) as e:
        raise Exception('AWS credentials are missing or incomplete.') from e
    except ClientError as e:
        raise Exception(f"Failed to subscribe SQS queue to SNS topic: {e}") from e

def retrieve_secret(secret_name: str) -> dict:
    """
    Retrieve a secret from AWS Secrets Manager.

    Args:
        secret_name (str): The name or ARN of the secret.

    Returns:
        dict: The secret value as a dictionary.

    Raises:
        NoCredentialsError: If AWS credentials are not found.
        PartialCredentialsError: If AWS credentials are incomplete.
        ClientError: If there is an error retrieving the secret.
    """
    try: 
        response = secretsmanager_client.get_secret_value(
            SecretId=secret_name,
        )
        secret = response.get('SecretString')
        return json.loads(secret)
    except (NoCredentialsError, PartialCredentialsError) as e:
        raise Exception('AWS credentials are missing or incomplete.') from e
    except ClientError as e:
        raise Exception(f"Failed to retrieve secret from Secrets Manager: {e}") from e

def decrypt_env_file(password: str, env_file: str, output_file: str = ".env") -> None:
    """
    Decrypt an encrypted environment file using GPG.

    Args:
        password (str): The passphrase used to decrypt the file.
        env_file (str): The path to the encrypted environment file.

    Returns:
        Dict[str, str]: A dictionary containing the decrypted environment variables.

    Raises:
        Exception: If decryption fails or the file cannot be read.
    """
    try:
        # Intialize GPG
        gpg = gnupg.GPG()
        
        # Read the encrypted file
        with open(env_file, 'rb') as file:
            decrypted_data = gpg.decrypt_file(file, passphrase=password)
        
        # Check if decryption was successful
        if not decrypted_data.ok:
            raise Exception('Failed to decrypt file.')
        
        # Split the decrypted data into lines and remove empty lines
        lines = [line.strip() for line in str(decrypted_data).splitlines() if line.strip()]
        
        # Write the decrypted data to the output file
        with open(output_file, 'w') as file:
            file.write('\n'.join(lines))
        
    except Exception as e:
        raise Exception(f"Failed to decrypt environment file: {e}") from e
    

def encrypt_env_file(password: str, output_env_file: str) -> None:
    """
    Encrypt the current environment variables into a file using GPG.

    Args:
        password (str): The passphrase used to encrypt the file.
        output_env_file (str): The path to save the encrypted environment file.

    Raises:
        Exception: If encryption fails or the file cannot be written.
    """
    try:
        # Initialize GPG
        gpg = gnupg.GPG()
        
        # Convert environment variables to a string
        env_data = '\n'.join([f"{key}={value}" for key, value in os.environ.items()])
        
        # Encrypt the data 
        encrypted_data = gpg.encrypt(env_data, recipients=None, symmetric=True, passphrase=password)
        
        # Check if encryption was successful
        if not encrypted_data.ok:
            raise Exception(f"Encryption failed: {encrypted_data.stderr}")

        # Write the encrypted data to the output file
        with open(output_env_file, 'wb') as file:
            file.write(encrypted_data.data)
    except Exception as e:
        raise Exception(f"Failed to encrypt environment file: {e}") from e

