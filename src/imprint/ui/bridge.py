"""Qt bridge between the QML interface and the v6 engine.

The bridge owns the worker thread, exposes typed properties to QML, and
converts engine pipeline events into UI state, result rows, and logs.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSettings,
    QSortFilterProxyModel,
    QStandardPaths,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices

from imprint import __version__
from imprint.domain.constants import CONFIG_FILENAME, MODEL_REGISTRY
from imprint.domain.results import ImageStatus, RunSummary
from imprint.domain.settings import (
    AnalysisSettings,
    PathSettings,
    validate_analysis_settings,
    validate_path_settings,
)
from imprint.engine.pipeline import EngineOptions, EngineV6
from imprint.events.pipeline import (
    Finished,
    Halted,
    ImageProcessed,
    PipelineEvent,
    Progress,
    RunStarted,
    SourceDiscovered,
    StageChanged,
    SummaryEvent,
)
from imprint.platform.config import ConfigManager
from imprint.platform.logging import configure_logging

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = Path.home() / ".imprint" / "embeddings.sqlite3"
UI_LOG_POLL_MS = 100
UI_LOG_MAX_ROWS = 2000

EngineFactory = Callable[..., EngineV6]


@dataclass(frozen=True)
class ResultRow:
    """One row in the live results grid."""

    file_name: str
    source_url: str
    score: float
    det_score: float
    status: str
    subfolder: str
    cached: bool
    error: str


class ResultsModel(QAbstractListModel):
    """Append-only list model of processed source images."""

    FileNameRole = int(Qt.ItemDataRole.UserRole) + 1
    SourceUrlRole = FileNameRole + 1
    ScoreRole = FileNameRole + 2
    DetScoreRole = FileNameRole + 3
    StatusRole = FileNameRole + 4
    SubfolderRole = FileNameRole + 5
    CachedRole = FileNameRole + 6
    ErrorRole = FileNameRole + 7

    countChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[ResultRow] = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.FileNameRole: QByteArray(b"fileName"),
            self.SourceUrlRole: QByteArray(b"sourceUrl"),
            self.ScoreRole: QByteArray(b"score"),
            self.DetScoreRole: QByteArray(b"detScore"),
            self.StatusRole: QByteArray(b"status"),
            self.SubfolderRole: QByteArray(b"subfolder"),
            self.CachedRole: QByteArray(b"cached"),
            self.ErrorRole: QByteArray(b"errorText"),
        }

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = 0) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        if role == self.FileNameRole or role == Qt.ItemDataRole.DisplayRole:
            return row.file_name
        if role == self.SourceUrlRole:
            return row.source_url
        if role == self.ScoreRole:
            return row.score
        if role == self.DetScoreRole:
            return row.det_score
        if role == self.StatusRole:
            return row.status
        if role == self.SubfolderRole:
            return row.subfolder
        if role == self.CachedRole:
            return row.cached
        if role == self.ErrorRole:
            return row.error
        return None

    def append_event(self, event: ImageProcessed) -> None:
        """Append one processed-image event."""
        row = ResultRow(
            file_name=event.source.name,
            source_url=QUrl.fromLocalFile(str(event.source)).toString(),
            score=event.score if event.score is not None else -1.0,
            det_score=event.det_score if event.det_score is not None else -1.0,
            status=event.status.name.lower(),
            subfolder=event.subfolder or "",
            cached=event.cached,
            error=event.error or "",
        )
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        self._rows.append(row)
        self.endInsertRows()
        self.countChanged.emit()

    def clear(self) -> None:
        """Remove every row."""
        if not self._rows:
            return
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()
        self.countChanged.emit()


class ResultFilterModel(QSortFilterProxyModel):
    """Filter results by status (all, match, skip, error)."""

    def __init__(self, source: ResultsModel, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.setSourceModel(source)
        self._status = "all"

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex
    ) -> bool:
        if self._status == "all":
            return True
        model = self.sourceModel()
        if model is None:  # pragma: no cover - source is always set
            return True
        index = model.index(source_row, 0, source_parent)
        status: object = model.data(index, ResultsModel.StatusRole)
        return status == self._status

    def set_filter(self, status: str) -> None:
        """Change the active status filter."""
        if status == self._status:
            return
        self._status = status
        self.invalidate()


class LogModel(QAbstractListModel):
    """Bounded list model for the activity log."""

    MessageRole = int(Qt.ItemDataRole.UserRole) + 1
    LevelRole = MessageRole + 1

    def __init__(self, max_rows: int = UI_LOG_MAX_ROWS, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[tuple[str, str]] = []
        self._max_rows = max(1, max_rows)

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.MessageRole: QByteArray(b"message"),
            self.LevelRole: QByteArray(b"level"),
        }

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = 0) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        level, message = self._rows[index.row()]
        if role == self.MessageRole or role == Qt.ItemDataRole.DisplayRole:
            return message
        if role == self.LevelRole:
            return level
        return None

    def append_log(self, level: str, message: str) -> None:
        """Append a log row, dropping the oldest rows when full."""
        if len(self._rows) >= self._max_rows:
            remove_count = len(self._rows) - self._max_rows + 1
            self.beginRemoveRows(QModelIndex(), 0, remove_count - 1)
            del self._rows[:remove_count]
            self.endRemoveRows()

        row = len(self._rows)
        self.beginInsertRows(QModelIndex(), row, row)
        self._rows.append((level, message))
        self.endInsertRows()

    def clear(self) -> None:
        """Remove every log row."""
        if not self._rows:
            return
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()


class EngineWorker(QObject):
    """Runs EngineV6 on a worker thread and forwards its events."""

    pipelineEvent = Signal(object)
    finished = Signal(object)

    def __init__(
        self,
        paths: PathSettings,
        analysis: AnalysisSettings,
        cancel_event: threading.Event,
        pause_event: threading.Event,
        options: EngineOptions,
        engine_factory: EngineFactory = EngineV6,
    ) -> None:
        super().__init__()
        self._paths = paths
        self._analysis = analysis
        self._cancel = cancel_event
        self._pause = pause_event
        self._options = options
        self._engine_factory = engine_factory

    @Slot()
    def run(self) -> None:
        """Execute the engine and report the final summary."""
        summary: RunSummary | None = None
        try:
            engine = self._engine_factory(
                paths=self._paths,
                analysis=self._analysis,
                emit=self.pipelineEvent.emit,
                cancel_event=self._cancel,
                pause_event=self._pause,
                options=self._options,
            )
            summary = engine.run()
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unhandled UI worker error")
            self.pipelineEvent.emit(Halted(f"An unexpected error occurred:\n\n{exc}"))
        finally:
            self.finished.emit(summary)


class AppBridge(QObject):
    """Expose application state and commands to QML."""

    statusChanged = Signal()
    progressChanged = Signal()
    countsChanged = Signal()
    foldersChanged = Signal()
    settingsChanged = Signal()
    summaryChanged = Signal()
    runningChanged = Signal()
    pausedChanged = Signal()
    modelChanged = Signal()
    resultFilterChanged = Signal()
    errorOccurred = Signal(str, str)

    def __init__(
        self,
        config_path: Path | None = None,
        log_dir: Path | None = None,
        *,
        config_manager: ConfigManager | None = None,
        qsettings: QSettings | None = None,
        engine_factory: EngineFactory = EngineV6,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if config_manager is None and config_path is None:
            config_dir = Path(
                QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
            )
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / CONFIG_FILENAME
        if log_dir is None:
            log_dir = (
                Path(
                    QStandardPaths.writableLocation(
                        QStandardPaths.StandardLocation.AppLocalDataLocation
                    )
                )
                / "logs"
            )
        self._config_manager = config_manager or ConfigManager(config_path)
        self._settings = self._config_manager.load()
        self._qsettings = qsettings or QSettings("Imprint", "Imprint Face Sorter")
        self._engine_factory = engine_factory

        self._results = ResultsModel(self)
        self._results_proxy = ResultFilterModel(self._results, self)
        self._results_proxy.set_filter("match")
        self._log = LogModel(parent=self)
        self._log_queue: queue.Queue[str] = queue.Queue()
        configure_logging(self._log_queue, log_dir=log_dir)
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(UI_LOG_POLL_MS)
        self._log_timer.timeout.connect(self._poll_logs)
        self._log_timer.start()

        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: QThread | None = None
        self._worker: EngineWorker | None = None
        self._running = False
        self._paused = False
        self._status_text = "Ready."
        self._progress_value = 0.0
        self._progress_text = "0 / 0"
        self._match_count = 0
        self._skip_count = 0
        self._error_count = 0
        self._processed_count = 0
        self._total_count = 0
        self._summary_text = ""
        self._result_filter = "match"

        self._model_names = [profile.display_name for profile in MODEL_REGISTRY.values()]
        self._model_index = next(
            (
                index
                for index, profile in enumerate(MODEL_REGISTRY.values())
                if profile.code_name == self._settings.analysis.model_name
            ),
            0,
        )

        self._window_width = int(str(self._qsettings.value("window/width", 1240)))
        self._window_height = int(str(self._qsettings.value("window/height", 820)))
        self._window_x = int(str(self._qsettings.value("window/x", 80)))
        self._window_y = int(str(self._qsettings.value("window/y", 60)))

        logger.info("Imprint v6 UI ready.")

    # -- Folder properties -------------------------------------------------

    def _get_reference_folder(self) -> str:
        return self._settings.paths.reference_folder

    def _set_reference_folder(self, value: str) -> None:
        value = value.strip()
        if value == self._settings.paths.reference_folder:
            return
        self._settings.paths.reference_folder = value
        self.foldersChanged.emit()

    referenceFolder = Property(
        str, _get_reference_folder, _set_reference_folder, notify=foldersChanged
    )

    def _get_source_folder(self) -> str:
        return self._settings.paths.source_folder

    def _set_source_folder(self, value: str) -> None:
        value = value.strip()
        if value == self._settings.paths.source_folder:
            return
        self._settings.paths.source_folder = value
        self.foldersChanged.emit()

    sourceFolder = Property(str, _get_source_folder, _set_source_folder, notify=foldersChanged)

    def _get_destination_folder(self) -> str:
        return self._settings.paths.destination_folder

    def _set_destination_folder(self, value: str) -> None:
        value = value.strip()
        if value == self._settings.paths.destination_folder:
            return
        self._settings.paths.destination_folder = value
        self.foldersChanged.emit()

    destinationFolder = Property(
        str, _get_destination_folder, _set_destination_folder, notify=foldersChanged
    )

    @Slot(str, QUrl)
    def setFolderFromUrl(self, kind: str, url: QUrl) -> None:
        """Set a folder from a QML URL (drag/drop or folder dialog)."""
        path = url.toLocalFile()
        if not path:
            return
        if kind == "reference":
            self._set_reference_folder(path)
        elif kind == "source":
            self._set_source_folder(path)
        elif kind == "destination":
            self._set_destination_folder(path)

    # -- Settings properties ----------------------------------------------

    @Property(list, constant=True)
    def modelDisplayNames(self) -> list[str]:
        """Human-readable model names for the selector."""
        return list(self._model_names)

    def _get_model_index(self) -> int:
        return self._model_index

    modelIndex = Property(int, _get_model_index, notify=modelChanged)

    @Slot(int)
    def selectModel(self, index: int) -> None:
        """Select a recognition model and apply its recommended settings."""
        if self._running or not 0 <= index < len(self._model_names):
            return
        profile = list(MODEL_REGISTRY.values())[index]
        self._model_index = index
        self._settings.analysis.model_name = profile.code_name
        self._settings.analysis.distance_threshold = profile.recommended_threshold
        self._settings.analysis.batch_size = profile.recommended_batch_size
        self.modelChanged.emit()
        self.settingsChanged.emit()
        logger.info("Selected model: %s", profile.display_name)

    def _get_distance_threshold(self) -> float:
        return self._settings.analysis.distance_threshold

    def _set_distance_threshold(self, value: float) -> None:
        value = max(0.01, float(value))
        if value == self._settings.analysis.distance_threshold:
            return
        self._settings.analysis.distance_threshold = value
        self.settingsChanged.emit()

    distanceThreshold = Property(
        float,
        _get_distance_threshold,
        _set_distance_threshold,
        notify=settingsChanged,
    )

    def _get_confidence_threshold(self) -> float:
        return self._settings.analysis.confidence_threshold

    def _set_confidence_threshold(self, value: float) -> None:
        value = min(1.0, max(0.0, float(value)))
        if value == self._settings.analysis.confidence_threshold:
            return
        self._settings.analysis.confidence_threshold = value
        self.settingsChanged.emit()

    confidenceThreshold = Property(
        float,
        _get_confidence_threshold,
        _set_confidence_threshold,
        notify=settingsChanged,
    )

    def _get_batch_size(self) -> int:
        return self._settings.analysis.batch_size

    def _set_batch_size(self, value: int) -> None:
        value = max(1, int(value))
        if value == self._settings.analysis.batch_size:
            return
        self._settings.analysis.batch_size = value
        self.settingsChanged.emit()

    batchSize = Property(int, _get_batch_size, _set_batch_size, notify=settingsChanged)

    def _get_number_of_subfolders(self) -> int:
        return self._settings.analysis.number_of_subfolders

    def _set_number_of_subfolders(self, value: int) -> None:
        value = max(1, int(value))
        if value == self._settings.analysis.number_of_subfolders:
            return
        self._settings.analysis.number_of_subfolders = value
        self.settingsChanged.emit()

    numberOfSubfolders = Property(
        int,
        _get_number_of_subfolders,
        _set_number_of_subfolders,
        notify=settingsChanged,
    )

    def _get_cache_enabled(self) -> bool:
        return self._settings.analysis.cache_enabled

    def _set_cache_enabled(self, value: bool) -> None:
        if value == self._settings.analysis.cache_enabled:
            return
        self._settings.analysis.cache_enabled = value
        self.settingsChanged.emit()

    cacheEnabled = Property(
        bool,
        _get_cache_enabled,
        _set_cache_enabled,
        notify=settingsChanged,
    )

    @Slot()
    def resetRecommended(self) -> None:
        """Reapply the selected model's recommended settings."""
        self.selectModel(self._model_index)

    # -- Run state properties ---------------------------------------------

    def _get_status_text(self) -> str:
        return self._status_text

    statusText = Property(str, _get_status_text, notify=statusChanged)

    def _get_progress_value(self) -> float:
        return self._progress_value

    progressValue = Property(float, _get_progress_value, notify=progressChanged)

    def _get_progress_text(self) -> str:
        return self._progress_text

    progressText = Property(str, _get_progress_text, notify=progressChanged)

    def _get_running(self) -> bool:
        return self._running

    running = Property(bool, _get_running, notify=runningChanged)

    def _get_paused(self) -> bool:
        return self._paused

    paused = Property(bool, _get_paused, notify=pausedChanged)

    def _get_match_count(self) -> int:
        return self._match_count

    matchCount = Property(int, _get_match_count, notify=countsChanged)

    def _get_skip_count(self) -> int:
        return self._skip_count

    skipCount = Property(int, _get_skip_count, notify=countsChanged)

    def _get_error_count(self) -> int:
        return self._error_count

    errorCount = Property(int, _get_error_count, notify=countsChanged)

    def _get_processed_count(self) -> int:
        return self._processed_count

    processedCount = Property(int, _get_processed_count, notify=countsChanged)

    def _get_total_count(self) -> int:
        return self._total_count

    totalCount = Property(int, _get_total_count, notify=countsChanged)

    def _get_summary_text(self) -> str:
        return self._summary_text

    summaryText = Property(str, _get_summary_text, notify=summaryChanged)

    def _get_result_filter(self) -> str:
        return self._result_filter

    def _set_result_filter(self, value: str) -> None:
        if value == self._result_filter:
            return
        self._result_filter = value
        self._results_proxy.set_filter(value)
        self.resultFilterChanged.emit()
        self.countsChanged.emit()

    resultFilter = Property(
        str,
        _get_result_filter,
        _set_result_filter,
        notify=resultFilterChanged,
    )

    @Property(QObject, constant=True)
    def resultsProxy(self) -> ResultFilterModel:
        """Filtered model consumed by the QML grid."""
        return self._results_proxy

    def _get_visible_result_count(self) -> int:
        return int(self._results_proxy.rowCount())

    visibleResultCount = Property(int, _get_visible_result_count, notify=countsChanged)

    @Slot(int, result="QVariantMap")
    def resultAt(self, index: int) -> dict[str, Any]:
        """Return one filtered result row as a QML-friendly mapping."""
        if index < 0 or index >= self._results_proxy.rowCount():
            return {}
        model_index = self._results_proxy.index(index, 0)
        return {
            "fileName": self._results_proxy.data(model_index, ResultsModel.FileNameRole),
            "sourceUrl": self._results_proxy.data(model_index, ResultsModel.SourceUrlRole),
            "score": self._results_proxy.data(model_index, ResultsModel.ScoreRole),
            "detScore": self._results_proxy.data(model_index, ResultsModel.DetScoreRole),
            "status": self._results_proxy.data(model_index, ResultsModel.StatusRole),
            "subfolder": self._results_proxy.data(model_index, ResultsModel.SubfolderRole),
            "cached": self._results_proxy.data(model_index, ResultsModel.CachedRole),
            "errorText": self._results_proxy.data(model_index, ResultsModel.ErrorRole),
        }

    @Property(QObject, constant=True)
    def logModel(self) -> LogModel:
        """Activity log model consumed by QML."""
        return self._log

    def _get_window_width(self) -> int:
        return self._window_width

    windowWidth = Property(int, _get_window_width, constant=True)

    def _get_window_height(self) -> int:
        return self._window_height

    windowHeight = Property(int, _get_window_height, constant=True)

    def _get_window_x(self) -> int:
        return self._window_x

    windowX = Property(int, _get_window_x, constant=True)

    def _get_window_y(self) -> int:
        return self._window_y

    windowY = Property(int, _get_window_y, constant=True)

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    # -- Engine lifecycle --------------------------------------------------

    @Slot()
    def startAnalysis(self) -> None:
        """Validate settings, persist them, and start the worker thread."""
        if self._running:
            return

        errors = validate_path_settings(self._settings.paths)
        errors += validate_analysis_settings(self._settings.analysis)
        if errors:
            message = "Please fix the following issues:\n\n" + "\n".join(
                f"\u2022 {error}" for error in errors
            )
            self._set_status("Validation failed.")
            self.errorOccurred.emit("Validation Error", message)
            return

        try:
            self._config_manager.save(self._settings)
        except OSError as exc:  # pragma: no cover - disk failure
            self.errorOccurred.emit("Configuration Error", str(exc))
            return

        self._results.clear()
        self._set_result_filter("match")
        self._log.clear()
        self._summary_text = ""
        self._match_count = 0
        self._skip_count = 0
        self._error_count = 0
        self._processed_count = 0
        self._total_count = 0
        self._progress_value = 0.0
        self._progress_text = "0 / 0"
        self._set_status("Starting analysis...")
        self.summaryChanged.emit()
        self.countsChanged.emit()
        self.progressChanged.emit()

        self._cancel_event.clear()
        self._pause_event.clear()
        self._paused = False
        self.pausedChanged.emit()

        cache_path = DEFAULT_CACHE_PATH if self._settings.analysis.cache_enabled else None
        options = EngineOptions(cache_path=cache_path)
        paths = replace(self._settings.paths)
        analysis = replace(self._settings.analysis)

        self._thread = QThread(self)
        self._worker = EngineWorker(
            paths=paths,
            analysis=analysis,
            cancel_event=self._cancel_event,
            pause_event=self._pause_event,
            options=options,
            engine_factory=self._engine_factory,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.pipelineEvent.connect(
            self._on_pipeline_event, Qt.ConnectionType.QueuedConnection
        )
        self._worker.finished.connect(self._on_engine_finished, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.finished.connect(self._thread.deleteLater)
        self._set_running(True)
        self._thread.start()

    @Slot()
    def cancelAnalysis(self) -> None:
        """Request cooperative cancellation."""
        if not self._running:
            return
        self._cancel_event.set()
        self._set_status("Cancelling analysis...")
        logger.warning("Cancel requested by user.")

    @Slot()
    def pauseAnalysis(self) -> None:
        """Pause the worker at the next safe checkpoint."""
        if not self._running or self._paused:
            return
        self._pause_event.set()
        self._paused = True
        self.pausedChanged.emit()
        self._set_status("Paused.")

    @Slot()
    def resumeAnalysis(self) -> None:
        """Resume a paused worker."""
        if not self._running or not self._paused:
            return
        self._pause_event.clear()
        self._paused = False
        self.pausedChanged.emit()
        self._set_status("Resuming...")

    @Slot()
    def togglePause(self) -> None:
        """Toggle between paused and running states."""
        if self._paused:
            self.resumeAnalysis()
        else:
            self.pauseAnalysis()

    @Slot()
    def openDestination(self) -> None:
        """Open the destination folder in the system file manager."""
        destination = Path(self._settings.paths.destination_folder)
        if not destination.is_dir():
            self.errorOccurred.emit(
                "Destination Folder",
                "The destination folder does not exist yet.",
            )
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(destination))):
            self.errorOccurred.emit(
                "Destination Folder",
                "Could not open the destination folder.",
            )

    @Slot()
    def clearLog(self) -> None:
        """Clear the activity log."""
        self._log.clear()

    @Slot(int, int, int, int)
    def saveWindowGeometry(self, width: int, height: int, x: int, y: int) -> None:
        """Persist the window geometry for the next launch."""
        self._qsettings.setValue("window/width", width)
        self._qsettings.setValue("window/height", height)
        self._qsettings.setValue("window/x", x)
        self._qsettings.setValue("window/y", y)
        self._qsettings.sync()

    @Slot()
    def shutdown(self) -> None:
        """Stop timers and wait briefly for a running worker."""
        self._log_timer.stop()
        if self._thread is not None and self._thread.isRunning():
            self._cancel_event.set()
            self._thread.quit()
            self._thread.wait(5000)
        try:
            self._config_manager.save(self._settings)
        except OSError:  # pragma: no cover - disk failure
            logger.warning("Could not save configuration on shutdown.")

    # -- Worker event handling ---------------------------------------------

    def _on_pipeline_event(self, event: PipelineEvent) -> None:
        if isinstance(event, RunStarted):
            self._set_status(f"Preparing '{event.model_name}' model...")
        elif isinstance(event, StageChanged):
            self._set_status(event.message)
        elif isinstance(event, SourceDiscovered):
            self._total_count = event.total
            self.countsChanged.emit()
        elif isinstance(event, Progress):
            self._set_progress(event.current, event.total, event.message)
        elif isinstance(event, ImageProcessed):
            self._results.append_event(event)
            self._processed_count += 1
            if event.status is ImageStatus.MATCH:
                self._match_count += 1
            elif event.status is ImageStatus.SKIP:
                self._skip_count += 1
            else:
                self._error_count += 1
            self.countsChanged.emit()
        elif isinstance(event, SummaryEvent):
            self._apply_summary(event.summary)
        elif isinstance(event, Halted):
            self._set_status("Analysis halted.")
            self.errorOccurred.emit("Analysis Halted", event.message)
        elif isinstance(event, Finished):
            self._set_running(False)

    def _on_engine_finished(self, summary: object) -> None:
        if isinstance(summary, RunSummary):
            self._apply_summary(summary)
        self._set_running(False)

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None

    def _apply_summary(self, summary: RunSummary) -> None:
        self._match_count = summary.matched
        self._skip_count = summary.skipped
        self._error_count = summary.errors
        self._processed_count = summary.processed
        self._total_count = summary.total
        self._progress_value = (
            summary.processed / summary.total if summary.cancelled and summary.total else 1.0
        )
        self._progress_text = f"{summary.processed} / {summary.total}"
        self._summary_text = summary.message()
        self._set_status("Analysis cancelled." if summary.cancelled else "Analysis complete.")
        self.summaryChanged.emit()
        self.countsChanged.emit()
        self.progressChanged.emit()

    def _set_status(self, text: str) -> None:
        if text == self._status_text:
            return
        self._status_text = text
        self.statusChanged.emit()

    def _set_progress(self, current: int, total: int, message: str) -> None:
        self._progress_value = current / total if total else 0.0
        self._progress_text = f"{current} / {total}"
        if message and message != self._status_text:
            self._status_text = message
            self.statusChanged.emit()
        self.progressChanged.emit()

    def _set_running(self, running: bool) -> None:
        changed = running != self._running
        self._running = running
        if not running and self._paused:
            self._paused = False
            self.pausedChanged.emit()
        if changed:
            self.runningChanged.emit()

    def _poll_logs(self) -> None:
        try:
            while True:
                record = self._log_queue.get_nowait()
                if ": " in record:
                    level, message = record.split(": ", 1)
                else:
                    level, message = "INFO", record
                self._log.append_log(level, message)
        except queue.Empty:
            pass
