"""Tests for result, filter, and log models."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt

from imprint.domain.results import ImageStatus
from imprint.events.pipeline import ImageProcessed
from imprint.ui.bridge import LogModel, ResultFilterModel, ResultsModel


def make_event(
    name: str,
    status: ImageStatus,
    score: float | None = 0.1,
    cached: bool = False,
) -> ImageProcessed:
    return ImageProcessed(
        source=Path("/tmp") / name,
        status=status,
        score=score,
        det_score=0.9,
        subfolder="Score_0.100_to_0.200" if status is ImageStatus.MATCH else None,
        destination=Path("/tmp/out") / name if status is ImageStatus.MATCH else None,
        cached=cached,
        error="broken" if status is ImageStatus.ERROR else None,
    )


class TestResultsModel:
    def test_roles_and_data(self) -> None:
        model = ResultsModel()
        model.append_event(make_event("match.png", ImageStatus.MATCH, cached=True))

        assert model.rowCount() == 1
        assert model.rowCount(QModelIndex()) == 1
        assert model.rowCount(model.index(0, 0)) == 0
        assert model.data(QModelIndex()) is None
        assert model.data(model.index(99, 0)) is None

        index = model.index(0, 0)
        assert model.data(index, ResultsModel.FileNameRole) == "match.png"
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "match.png"
        assert model.data(index, ResultsModel.SourceUrlRole).endswith("match.png")
        assert model.data(index, ResultsModel.ScoreRole) == 0.1
        assert model.data(index, ResultsModel.DetScoreRole) == 0.9
        assert model.data(index, ResultsModel.StatusRole) == "match"
        assert model.data(index, ResultsModel.SubfolderRole) == "Score_0.100_to_0.200"
        assert model.data(index, ResultsModel.CachedRole) is True
        assert model.data(index, ResultsModel.ErrorRole) == ""
        assert model.data(index, Qt.ItemDataRole.ToolTipRole) is None
        assert b"fileName" in model.roleNames().values()

    def test_missing_values_and_clear(self) -> None:
        model = ResultsModel()
        model.append_event(ImageProcessed(source=Path("skip.png"), status=ImageStatus.SKIP))
        index = model.index(0, 0)
        assert model.data(index, ResultsModel.ScoreRole) == -1.0
        assert model.data(index, ResultsModel.DetScoreRole) == -1.0
        assert model.data(index, ResultsModel.SubfolderRole) == ""
        assert model.data(index, ResultsModel.ErrorRole) == ""

        model.clear()
        assert model.rowCount() == 0
        model.clear()
        assert model.rowCount() == 0


class TestResultFilterModel:
    def test_filters_by_status(self) -> None:
        source = ResultsModel()
        source.append_event(make_event("match.png", ImageStatus.MATCH))
        source.append_event(make_event("skip.png", ImageStatus.SKIP))
        source.append_event(make_event("error.png", ImageStatus.ERROR))
        proxy = ResultFilterModel(source)

        assert proxy.rowCount() == 3
        proxy.set_filter("match")
        assert proxy.rowCount() == 1
        assert proxy.data(proxy.index(0, 0), ResultsModel.FileNameRole) == "match.png"

        proxy.set_filter("skip")
        assert proxy.rowCount() == 1
        proxy.set_filter("error")
        assert proxy.rowCount() == 1
        proxy.set_filter("all")
        assert proxy.rowCount() == 3

        proxy.set_filter("all")
        assert proxy.rowCount() == 3


class TestLogModel:
    def test_roles_and_cap(self) -> None:
        model = LogModel(max_rows=2)
        model.append_log("INFO", "first")
        model.append_log("WARNING", "second")
        model.append_log("ERROR", "third")

        assert model.rowCount() == 2
        assert model.rowCount(model.index(0, 0)) == 0
        assert b"message" in model.roleNames().values()
        index = model.index(0, 0)
        assert model.data(index, LogModel.LevelRole) == "WARNING"
        assert model.data(index, LogModel.MessageRole) == "second"
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "second"
        assert model.data(QModelIndex()) is None
        assert model.data(model.index(99, 0)) is None
        assert model.data(index, Qt.ItemDataRole.ToolTipRole) is None

        model.clear()
        assert model.rowCount() == 0
        model.clear()
        assert model.rowCount() == 0
