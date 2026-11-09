"""Verify that the v6 engine produces exactly the same output as v5."""

from __future__ import annotations

import threading
from pathlib import Path

from imprint.engine import LegacySorterEngine
from imprint.engine.pipeline import EngineV6
from imprint.events import EngineEvent, EventType
from imprint.events.pipeline import SummaryEvent
from tests.engine.helpers import (
    MarkerAnalyser,
    make_engine_env,
    reference_mapping,
    snapshot,
    source_mapping,
)


def merged_mapping() -> dict:
    return {**reference_mapping(), **source_mapping()}


def test_v6_matches_legacy_outputs_and_summary(tmp_path: Path) -> None:
    legacy_paths, legacy_analysis = make_engine_env(tmp_path / "legacy")
    new_paths, new_analysis = make_engine_env(tmp_path / "v6")

    legacy_events: list[EngineEvent] = []
    LegacySorterEngine(
        paths=legacy_paths,
        analysis=legacy_analysis,
        emit=legacy_events.append,
        cancel_event=threading.Event(),
        face_analyser=MarkerAnalyser(merged_mapping()),
    ).run()

    new_events: list = []
    summary = EngineV6(
        paths=new_paths,
        analysis=new_analysis,
        emit=new_events.append,
        cancel_event=threading.Event(),
        face_analyser=MarkerAnalyser(merged_mapping()),
    ).run()

    assert summary is not None
    legacy_destination = Path(legacy_paths.destination_folder)
    new_destination = Path(new_paths.destination_folder)
    assert snapshot(new_destination) == snapshot(legacy_destination)
    assert len(summary.matches) == 4

    legacy_summaries = [
        event.message
        for event in legacy_events
        if event.event_type == EventType.MESSAGE and "Analysis Complete!" in event.message
    ]
    assert len(legacy_summaries) == 1
    assert legacy_summaries[0].strip() == summary.message().strip()

    summary_events = [event for event in new_events if isinstance(event, SummaryEvent)]
    assert len(summary_events) == 1
    assert summary_events[0].summary == summary
