"""Unit tests for imprint.events.

Covers the EngineEvent dataclass, its factory methods, and the
EventType and MessageLevel enums.
"""

from __future__ import annotations

import pytest

from imprint.events import EngineEvent, EventType, MessageLevel


class TestEventType:
    """Tests for the EventType enum."""

    def test_all_expected_members_exist(self) -> None:
        """All expected event types should be defined."""
        expected = {"PROGRESS", "STATUS", "MESSAGE", "HALTED", "FINISHED", "LOG"}
        actual = {member.name for member in EventType}
        assert expected == actual


class TestMessageLevel:
    """Tests for the MessageLevel enum."""

    def test_info_value(self) -> None:
        """INFO should have value 'info'."""
        assert MessageLevel.INFO.value == "info"

    def test_warning_value(self) -> None:
        """WARNING should have value 'warning'."""
        assert MessageLevel.WARNING.value == "warning"

    def test_error_value(self) -> None:
        """ERROR should have value 'error'."""
        assert MessageLevel.ERROR.value == "error"


class TestEngineEvent:
    """Tests for the EngineEvent dataclass and its factory methods."""

    def test_immutability(self) -> None:
        """EngineEvent should be frozen (immutable)."""
        event = EngineEvent(event_type=EventType.STATUS, message="test")
        with pytest.raises(AttributeError):
            event.message = "changed"  # type: ignore[misc]

    def test_progress_factory(self) -> None:
        """progress() should create a correctly-typed event."""
        event = EngineEvent.progress(10, 100, "Working...")
        assert event.event_type == EventType.PROGRESS
        assert event.current == 10
        assert event.total == 100
        assert event.message == "Working..."

    def test_status_factory(self) -> None:
        """status() should create a correctly-typed event."""
        event = EngineEvent.status("Loading model...")
        assert event.event_type == EventType.STATUS
        assert event.message == "Loading model..."

    def test_show_message_factory(self) -> None:
        """show_message() should create a correctly-typed event."""
        event = EngineEvent.show_message(MessageLevel.ERROR, "Something broke")
        assert event.event_type == EventType.MESSAGE
        assert event.level == MessageLevel.ERROR
        assert event.message == "Something broke"

    def test_halted_factory_with_reason(self) -> None:
        """halted() should include the reason message."""
        event = EngineEvent.halted("Not enough references")
        assert event.event_type == EventType.HALTED
        assert event.message == "Not enough references"

    def test_halted_factory_without_reason(self) -> None:
        """halted() with no argument should have empty message."""
        event = EngineEvent.halted()
        assert event.event_type == EventType.HALTED
        assert event.message == ""

    def test_finished_factory(self) -> None:
        """finished() should create a FINISHED event."""
        event = EngineEvent.finished()
        assert event.event_type == EventType.FINISHED

    def test_default_level_is_info(self) -> None:
        """Default message level should be INFO."""
        event = EngineEvent(event_type=EventType.STATUS)
        assert event.level == MessageLevel.INFO
