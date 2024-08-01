import logging
from logging.handlers import RotatingFileHandler

class AppLogger:
    def __init__(self, name=__name__, log_file='Logs/logs.txt', max_file_size=5*1024*1024, backup_count=5):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(log_file, maxBytes=max_file_size, backupCount=backup_count)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def get_logger(self):
        return self.logger
    
