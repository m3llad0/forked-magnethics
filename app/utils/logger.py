import logging
from logging.handlers import RotatingFileHandler

def initialize_logger(name: str = "app", log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    """
    Initializes a logger with console and file handlers.

    :param name: Name of the logger.
    :param log_file: File to store logs.
    :param level: Logging level (e.g., logging.INFO, logging.DEBUG).
    :return: Configured logger instance.
    """
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if the logger is initialized multiple times
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler with log rotation
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger