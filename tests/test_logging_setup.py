"""Tests for the logging setup module."""

from __future__ import annotations

import logging
import queue
from pathlib import Path
from unittest.mock import patch

from imprint.logging_setup import QueueHandler, configure_logging


def test_queue_handler_error_handling() -> None:
    """Verify that QueueHandler.emit calls handleError on exception."""
    log_queue: queue.Queue[str] = queue.Queue()
    handler = QueueHandler(log_queue)

    dummy_record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # We patch the queue.put to raise an exception, triggering the except block
    with patch.object(log_queue, "put", side_effect=RuntimeError("Queue broken")):
        with patch.object(handler, "handleError") as mock_handle_error:
            handler.emit(dummy_record)
            mock_handle_error.assert_called_once_with(dummy_record)


def test_configure_logging(tmp_path: Path) -> None:
    """Verify configure_logging attaches all three handlers properly."""
    log_queue: queue.Queue[str] = queue.Queue()

    logger = configure_logging(log_queue, log_dir=tmp_path)

    assert logger.level == logging.INFO
    assert len(logger.handlers) == 3

    handler_types = [type(h) for h in logger.handlers]
    assert logging.StreamHandler in handler_types
    assert QueueHandler in handler_types
    assert logging.handlers.RotatingFileHandler in handler_types

    # Re-configuring should clear existing handlers (still 3 total)
    logger = configure_logging(log_queue, log_dir=tmp_path)
    assert len(logger.handlers) == 3

    # Verify fallback when log_dir is None
    with patch("imprint.logging_setup.Path.cwd", return_value=tmp_path):
        logger_none = configure_logging(log_queue, log_dir=None)
        assert len(logger_none.handlers) == 3
