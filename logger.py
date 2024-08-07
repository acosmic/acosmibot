# import logging
# from logging.handlers import RotatingFileHandler

# class AppLogger:
#     def __init__(self, name=__name__, log_file='Logs/logs.txt', max_file_size=5*1024*1024, backup_count=5):
#         self.logger = logging.getLogger(name)
#         self.logger.setLevel(logging.DEBUG)
#         handler = RotatingFileHandler(log_file, maxBytes=max_file_size, backupCount=backup_count)
#         formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
#         handler.setFormatter(formatter)
#         self.logger.addHandler(handler)

#     def get_logger(self):
#         return self.logger
    
import logging
from logging.handlers import TimedRotatingFileHandler
import os

class AppLogger:
    def __init__(self, name=__name__, log_dir='Logs', log_file='logs.txt', when='midnight', interval=1, backup_count=30):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Print the current working directory
        print(f"Current working directory: {os.getcwd()}")

        # Ensure the log directory exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Use an absolute path for the log file
        log_path = os.path.abspath(os.path.join(log_dir, log_file))
        print(f"Resolved log path: {log_path}")

        handler = TimedRotatingFileHandler(log_path, when=when, interval=interval, backupCount=backup_count)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)

        # Clear any existing handlers attached to the root logger
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Add the handler to the root logger
        logging.root.addHandler(handler)
        logging.root.setLevel(logging.DEBUG)

        # Configure the discord logger
        discord_logger = logging.getLogger('discord')
        discord_logger.addHandler(handler)
        discord_logger.setLevel(logging.INFO)

    def get_logger(self):
        return self.logger

