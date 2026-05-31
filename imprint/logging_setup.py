"""Logging infrastructure for the Imprint application.

Provides a :class:`QueueHandler` that forwards log records to a
:class:`queue.Queue` for thread-safe consumption by the GUI, and a
helper to configure the root logger with both console and rotating
file outputs.
"""

from __future__ import annotations

import logging
import queue
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class QueueHandler(logging.Handler):
    """Logging handler that puts formatted messages onto a queue.

    The GUI polls this queue on the main thread to safely append log
    lines to the ScrolledText widget.

    Attributes:
        log_queue: The queue that receives formatted log strings.
    """

    def __init__(self, log_queue: queue.Queue[str]) -> None:
        """Initialise the handler with a target queue.

        Args:
            log_queue: Destination queue for formatted log records.
        """
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        """Format and enqueue a log record.

        Args:
            record: The log record to process.
        """
        try:
            self.log_queue.put(self.format(record))
        except Exception:
            self.handleError(record)


def configure_logging(
    log_queue: queue.Queue[str],
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure the application-wide logger.

    Sets up three handlers on the root logger:

    1. **Console** — writes to stderr with timestamps.
    2. **Queue** — feeds the GUI log panel (level + message only).
    3. **Rotating file** — persists logs to disk (max 5 MB, 3 backups).

    Args:
        log_queue: Queue for the GUI handler.
        log_dir: Directory for log files.  Defaults to the current
            working directory.
        level: Logging level for all handlers.

    Returns:
        The configured root :class:`logging.Logger`.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Avoid adding duplicate handlers on re-init
    logger.handlers.clear()

    # Console handler
    console_fmt = logging.Formatter(
        "%(asctime)s — %(levelname)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # Queue handler (for GUI)
    queue_fmt = logging.Formatter("%(levelname)s: %(message)s")
    q_handler = QueueHandler(log_queue)
    q_handler.setFormatter(queue_fmt)
    logger.addHandler(q_handler)

    # Rotating file handler
    if log_dir is None:
        log_dir = Path.cwd()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "imprint.log"

    file_fmt = logging.Formatter(
        "%(asctime)s — %(name)s — %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger
