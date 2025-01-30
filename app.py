import os
from dotenv import load_dotenv
from helpers import logger
from services import reversion, data, momentum



if __name__ == '__main__':
    # Set up logger
    logger = logger.Logger('app.py')
    
    # Decrypt the env file, different for local and cloud environments
    try:
        if os.environ.get('LOCAL') == True:
            pass
        else:
            pass
    except Exception as e:
        logger.error(f'Error decrypting env file: {e}')
    
    # Load the decrypted env file
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