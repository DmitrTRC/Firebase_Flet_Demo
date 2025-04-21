import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[41m\033[37m',  # White on Red background
        'RESET': '\033[0m'  # Reset to default
    }

    def format(self, record):
        log_message = super().format(record)
        levelname = record.levelname
        if levelname in self.COLORS:
            return f"{self.COLORS[levelname]}{log_message}{self.COLORS['RESET']}"
        return log_message


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Set up and return a logger with colored output"""
    if level is None:
        level = logging.INFO

    _logger = logging.getLogger(name)
    _logger.setLevel(level)

    # Create a handler for console output
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create a formatter with timestamps and log level
    formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add the handler to the logger
    _logger.addHandler(handler)

    return _logger


# Create a default logger for import
logger = setup_logger("backend")
