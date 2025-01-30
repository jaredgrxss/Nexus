from pythonjsonlogger import jsonlogger
import sys

class Logger:
    def __init__(self, filename: str):
        # Set up logger
        self.logger = jsonlogger.JsonLogger(filename)
        self.logger.setLevel(jsonlogger.DEBUG)
        # Custom formatter
        fmt = self.logger.JsonFormatter(
            '%(name)s %(asctime)s %(levelname)s %(filename)s %(lineno)s %(process)d %(message)s',
            rename_fields={'levelname': 'severity', 'asctime': 'timestamp'}
        )
        # Stream handler
        stdoutHandler = jsonlogger.StreamHandler(stream=sys.stdout)
        stdoutHandler.setFormatter(fmt)
        
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