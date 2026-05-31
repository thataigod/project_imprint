"""Typed event protocol for engine-to-GUI communication.

The :class:`EngineEvent` dataclass carries a discriminated payload from
the worker thread to the GUI.  The GUI decodes events by matching on
:attr:`EngineEvent.event_type` using the :class:`EventType` enum.

This design eliminates magic strings and ad-hoc tuples, making the
inter-thread contract explicit, type-checked, and extensible.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    """Discriminator for :class:`EngineEvent` payloads.

    Members:
        PROGRESS: Periodic progress update (current, total, label).
        STATUS: Free-form status text for the status bar.
        MESSAGE: Request to show a modal messagebox (level + text).
        HALTED: Analysis could not start; engine is idle.
        FINISHED: Analysis completed (successfully or after cancel).
    """

    PROGRESS = auto()
    STATUS = auto()
    MESSAGE = auto()
    HALTED = auto()
    FINISHED = auto()


class MessageLevel(Enum):
    """Severity level for :attr:`EventType.MESSAGE` events.

    Members:
        INFO: Informational popup.
        WARNING: Warning popup.
        ERROR: Error popup.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class EngineEvent:
    """Immutable event emitted by the sorter engine.

    Attributes:
        event_type: Discriminator that determines how ``payload`` is interpreted.
        message: Human-readable description for logging / status display.
        current: Numerator for progress calculation (PROGRESS events only).
        total: Denominator for progress calculation (PROGRESS events only).
        level: Severity for MESSAGE events.
    """

    event_type: EventType
    message: str = ""
    current: int = 0
    total: int = 0
    level: MessageLevel = MessageLevel.INFO

    # -- Factory helpers ----------------------------------------------------

    @classmethod
    def progress(cls, current: int, total: int, message: str) -> EngineEvent:
        """Create a PROGRESS event.

        Args:
            current: Number of items processed so far.
            total: Total items to process.
            message: Status label for the progress bar.

        Returns:
            A new ``EngineEvent`` with ``event_type=PROGRESS``.
        """
        return cls(
            event_type=EventType.PROGRESS,
            message=message,
            current=current,
            total=total,
        )

    @classmethod
    def status(cls, message: str) -> EngineEvent:
        """Create a STATUS event.

        Args:
            message: Free-form status text.

        Returns:
            A new ``EngineEvent`` with ``event_type=STATUS``.
        """
        return cls(event_type=EventType.STATUS, message=message)

    @classmethod
    def show_message(
        cls, level: MessageLevel, message: str
    ) -> EngineEvent:
        """Create a MESSAGE event requesting a modal dialog.

        Args:
            level: Severity (info / warning / error).
            message: Text body of the dialog.

        Returns:
            A new ``EngineEvent`` with ``event_type=MESSAGE``.
        """
        return cls(event_type=EventType.MESSAGE, message=message, level=level)

    @classmethod
    def halted(cls, reason: str = "") -> EngineEvent:
        """Create a HALTED event.

        Args:
            reason: Optional explanation of why the analysis was halted.

        Returns:
            A new ``EngineEvent`` with ``event_type=HALTED``.
        """
        return cls(event_type=EventType.HALTED, message=reason)

    @classmethod
    def finished(cls) -> EngineEvent:
        """Create a FINISHED event.

        Returns:
            A new ``EngineEvent`` with ``event_type=FINISHED``.
        """
        return cls(event_type=EventType.FINISHED)
