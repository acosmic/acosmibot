import logging
from logging.handlers import TimedRotatingFileHandler
import os

class AppLogger:
    def __init__(self, name=__name__, log_dir='Logs', log_file='logs.txt', when='midnight', interval=1, backup_count=30):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

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

        # Suppress lower-level logs for specific libraries
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.WARNING)

    def get_logger(self):
        return self.logger

