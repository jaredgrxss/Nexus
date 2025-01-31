import os
from dotenv import load_dotenv
from helpers import logger, cloud
from services import reversion, data, momentum

if __name__ == '__main__':
    # Set up logger
    logger = logger.Logger('app.py')
    # Decrypt the env file, different for local and cloud environments
    passphrase = None
    try:
        if os.environ.get('LOCAL') == 'True':
            passphrase = os.environ.get('PASSPHRASE')
        else:
            passphrase = cloud.retrieve_secret(os.environ.get('PASSPHRASE'))
    except Exception as e:
        logger.error(f'Error fetching passphrase: {e}')
        exit(1)
    # Decrypt the env file based on the deployment environment
    try:
        cloud.decrypt_env_file(passphrase, os.environ.get('ENV_FILE'))
        logger.info(
            f"Successfully decrypted env file {os.environ.get('ENV_FILE')}"
        )
    except Exception as e:
        logger.error(f"Error in decrypting env file: {e}")
    # Load secrets from the env file
    load_dotenv()
    # Run the respective service
    match os.environ.get('SERVICE'):
        case 'Data':
            logger.info('Running Data service...')
            data.run()
        case 'Reversion':
            logger.info('Running Reversion service...')
            reversion.run()
        case 'Momentum':
            momentum.run()
