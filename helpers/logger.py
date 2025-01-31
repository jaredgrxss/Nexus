import sys
import logging

class Logger:
    def __init__(self, filename: str):
        # Set up logger
        self.logger = logging.getLogger(filename)
        self.logger.setLevel(logging.DEBUG)
        
        # Custom formatter
        fmt = logging.Formatter(
            '%(name)s %(asctime)s %(levelname)s %(filename)s %(lineno)s %(process)d %(message)s'
        )
        # Stream handler
        errHandler = logging.FileHandler('error.log')
        stdoutHandler = logging.StreamHandler(stream=sys.stdout)
        
        # Set levels
        stdoutHandler.setLevel(logging.DEBUG)
        errHandler.setLevel(logging.ERROR)
        
        # Set formatting
        stdoutHandler.setFormatter(fmt)
        errHandler.setFormatter(fmt)
        
        # Add handlers
        self.logger.addHandler(stdoutHandler)
        self.logger.addHandler(errHandler)
        
    def debug(self, message: str):
        self.logger.debug(message)
        
    def info(self, message: str):
        self.logger.info(message)
        
    def warning(self, message: str):
        self.logger.warning(message)
        
    def error(self, message: str):
        self.logger.error(message)
        
    def critical(self, message: str):
        self.logger.critical(message)