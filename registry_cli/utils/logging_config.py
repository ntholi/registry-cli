import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


class LoggingConfig:
    """Centralized logging configuration for the registry CLI application."""

    def __init__(self):
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        self._configured = False

    def setup_logging(
        self,
        log_level: str = "INFO",
        console_level: Optional[str] = None,
        file_level: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
        log_format: Optional[str] = None,
    ) -> None:
        """
        Set up centralized logging configuration.

        Args:
            log_level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_level: Log level for console output (if different from log_level)
            file_level: Log level for file output (if different from log_level)
            max_file_size: Maximum size of log files before rotation (in bytes)
            backup_count: Number of backup files to keep
            log_format: Custom log format string
        """
        if self._configured:
            return

        # Convert string levels to logging constants
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        root_level = level_map.get(log_level.upper(), logging.INFO)
        console_log_level = level_map.get(
            (console_level or log_level).upper(), root_level
        )
        file_log_level = level_map.get((file_level or log_level).upper(), root_level)

        # Default log format
        if not log_format:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(min(console_log_level, file_log_level))

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_log_level)
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler with rotation
        main_log_file = self.logs_dir / "registry-cli.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(file_log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        self._configured = True

        # Log the configuration
        logger = logging.getLogger(__name__)
        logger.info(
            f"Logging configured - Console: {console_level or log_level}, File: {file_level or log_level}"
        )
        logger.info(f"Log files will be stored in: {self.logs_dir.absolute()}")

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Logger instance
        """
        return logging.getLogger(name)

    def create_specialized_logger(
        self,
        name: str,
        log_file: str,
        level: str = "INFO",
        max_file_size: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        log_format: Optional[str] = None,
    ) -> logging.Logger:
        """
        Create a specialized logger that writes to a specific file.

        Args:
            name: Logger name
            log_file: Log file name (will be created in logs directory)
            level: Log level for this logger
            max_file_size: Maximum size of log files before rotation
            backup_count: Number of backup files to keep
            log_format: Custom log format string

        Returns:
            Specialized logger instance
        """
        if not log_format:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        logger = logging.getLogger(name)
        logger.setLevel(level_map.get(level.upper(), logging.INFO))

        # Check if handler already exists to avoid duplicates
        if not any(
            isinstance(h, logging.handlers.RotatingFileHandler)
            and h.baseFilename == str(self.logs_dir / log_file)
            for h in logger.handlers
        ):

            file_handler = logging.handlers.RotatingFileHandler(
                self.logs_dir / log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding="utf-8",
            )
            formatter = logging.Formatter(log_format)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger


# Global instance
_logging_config = LoggingConfig()


def setup_logging(**kwargs) -> None:
    """Convenience function to set up logging."""
    _logging_config.setup_logging(**kwargs)


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger."""
    return _logging_config.get_logger(name)


def create_specialized_logger(name: str, log_file: str, **kwargs) -> logging.Logger:
    """Convenience function to create a specialized logger."""
    return _logging_config.create_specialized_logger(name, log_file, **kwargs)


def configure_from_env() -> None:
    """Configure logging from environment variables."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    console_level = os.getenv("CONSOLE_LOG_LEVEL")
    file_level = os.getenv("FILE_LOG_LEVEL")

    setup_logging(
        log_level=log_level, console_level=console_level, file_level=file_level
    )
