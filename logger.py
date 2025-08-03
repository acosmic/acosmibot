import os
import logging
from logging.handlers import TimedRotatingFileHandler

class SizeAndTimeRotatingHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='midnight', interval=1, backupCount=30, maxBytes=2*1024*1024, encoding=None):
        super().__init__(filename, when, interval, backupCount, encoding=encoding)
        self.maxBytes = maxBytes

    def shouldRollover(self, record):
        # Time-based rollover
        if super().shouldRollover(record):
            return 1

        # Size-based rollover
        if self.maxBytes > 0:
            self.stream = self.stream or self._open()
            self.stream.flush()
            try:
                current_size = os.stat(self.baseFilename).st_size
                record_size = len((self.format(record) + '\n').encode('utf-8'))
                if current_size + record_size >= self.maxBytes:
                    return 1
            except FileNotFoundError:
                return 0
        return 0

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

        handler = SizeAndTimeRotatingHandler(
            log_path,
            when=when,
            interval=interval,
            backupCount=backup_count,
            maxBytes=2 * 1024 * 1024  # 2 MB
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)

        # Clear any existing handlers attached to the root logger
        for h in logging.root.handlers[:]:
            logging.root.removeHandler(h)

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
