# Imprint GPU Face Sorter

A high-performance, GPU-accelerated desktop application for sorting images based on facial similarity. Powered by state-of-the-art face recognition models, Imprint automatically identifies faces in your photos and organises them into scored subdirectories with a single click.

> **v6 modernization** — the PySide6/QML interface is now the default. See [`docs/adr/0001-v6-modern-rewrite.md`](docs/adr/0001-v6-modern-rewrite.md).
>
> Launch with `start.bat` or `python run.py`. The legacy Tkinter interface remains available
> during the transition with `start.bat --legacy` or `python run.py --legacy`.

## Features

- **State-of-the-Art Recognition** — Choose from multiple InsightFace models: *Antelope v2* (maximum accuracy), *Buffalo L* (balanced), or *Buffalo S* (fastest).
- **Automated Reference Pruning** — Provide multiple reference photos and the app intelligently finds the most consistent "core" group using a medoid-based algorithm, discarding outliers like blurry shots or side profiles.
- **Modern Desktop UI** — A themed PySide6/QML interface with drag-and-drop folder cards, model selection, live result thumbnails, filters, progress, and an activity log. The legacy Tkinter interface remains available with `--legacy`.
- **Dynamic Subfolder Organisation** — Matched images are automatically sorted into tiered subdirectories by similarity score (e.g. `Score_0.250_to_0.300/`).
- **Thread-Safe Architecture** — All GPU work runs on a background thread with a typed event system, ensuring the UI stays responsive and crash-free.
- **Persistent Configuration** — Folder paths and settings are saved to `config.ini` and restored on next launch.
- **Smart Launcher** — A `start.bat` script handles virtual environment creation and dependency installation automatically.
- **Duplicate-Safe Copying** — Images with identical filenames from different source subdirectories are renamed with `_1`, `_2` suffixes instead of being silently skipped.

## Requirements

| Requirement | Details |
|---|---|
| **OS** | Windows 10 / 11 |
| **GPU** | NVIDIA with CUDA support |
| **Python** | 3.12, added to PATH |
| **CUDA Toolkit** | Version 12.x (12.8 recommended) |
| **cuDNN** | 9.x for CUDA 12.x |

## Setup & Installation

### 1. Install CUDA and cuDNN (one-time)

1. Install the [NVIDIA CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads) using the "Express" option.
2. Download [cuDNN 9.x for CUDA 12.x](https://developer.nvidia.com/cudnn).
3. Unzip cuDNN and copy the contents of `bin/`, `include/`, and `lib/` into your CUDA installation directory (e.g. `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8`).

The packaged application does not bundle the CUDA or cuDNN runtimes; install them on the target machine.

### 2. Download the Project

Place all project files into a new folder:

```
project_imprint/
├── start.bat
├── run.py
├── requirements.txt
├── src/
│   └── imprint/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── domain/       # constants, settings, math
│       ├── engine/       # sorter engine (v5 legacy during transition)
│       ├── events/       # typed engine events
│       ├── gui/          # legacy Tkinter interface
│       ├── platform/     # config persistence, logging
│       └── ui/           # v6 PySide6/QML interface
└── tests/
    ├── unit/
    └── ...
```

### 3. Launch

Double-click **`start.bat`**. On first run it will:
1. Check for Python 3.12
2. Create a virtual environment (`imprint_env/`)
3. Install all dependencies from `requirements.txt`

Subsequent launches skip straight to the v6 QML application. Launch the legacy Tkinter
interface with `start.bat --legacy` or `python run.py --legacy`.

## Usage

1. **Select Folders**
   - **Reference Folder** — Multiple clear photos of the face you want to find.
   - **Source Folder** — All images to sort through (searched recursively).
   - **Destination Folder** — Where matched images are copied.

2. **Configure Settings**
   - Select a **Recognition Model** — this auto-populates recommended threshold and batch size.
   - Adjust **Distance Threshold** (lower = stricter), **Face Confidence** (0.0–1.0), **Batch Size**, and **Number of Subfolders** as needed.
   - Each setting includes inline help; the legacy interface uses hover tooltips.

3. **Run Analysis**
   - Click **"Save Config & Run Analysis"**. Monitor the progress bar and live log.
   - Click **"Cancel"** to stop early — partial results are preserved.

## Configuration (`config.ini`)

The application auto-manages a `config.ini` file. Example:

```ini
[Paths]
reference_folder = C:/Photos/Reference
source_folder = C:/Photos/Unsorted
destination_folder = C:/Photos/Matched

[Settings]
model_name = antelopev2
distance_threshold = 0.5
confidence_threshold = 0.85
batch_size = 8
number_of_subfolders = 10
```

### Settings Reference

| Setting | Type | Range | Description |
|---|---|---|---|
| `model_name` | string | `antelopev2`, `buffalo_l`, `buffalo_s` | Recognition model to use |
| `distance_threshold` | float | > 0 | Max cosine distance for a match (lower = stricter) |
| `confidence_threshold` | float | 0.0–1.0 | Min face-detection confidence |
| `batch_size` | int | ≥ 1 | Progress update grouping size |
| `number_of_subfolders` | int | ≥ 1 | Tiered output subdirectory count |

## How It Works

### 1. Build Core Reference Set

The app extracts face embeddings from every image in the reference folder that meets the confidence threshold. It computes an all-pairs cosine-distance matrix, finds the **medoid** (most representative face), and prunes any references whose distance to the medoid exceeds the threshold.

### 2. Process Source Images

Each source image is scanned for faces. The highest-confidence detection is compared against the core reference set using **vectorised numpy operations** for speed.

### 3. Sort into Scored Subfolders

If the closest distance to any reference is below the threshold, the image is copied into a subfolder named by its score range. Duplicate filenames are handled automatically with `_N` suffixes.

## Architecture

The application is split into focused, testable modules:

```
src/imprint/
├── __init__.py          # Package metadata and version
├── __main__.py          # python -m imprint entry point
├── app.py               # v6 composition root (placeholder)
├── domain/
│   ├── constants.py     # Named constants, model registry
│   ├── settings.py      # Typed settings + validation
│   └── math.py          # Vectorised cosine distance functions
├── engine/
│   ├── __init__.py      # Public engine exports
│   └── legacy.py        # v5 SorterEngine during the transition
├── events/
│   ├── __init__.py      # Public event exports
│   └── types.py         # Typed event system (Enum + dataclass)
├── platform/
│   ├── config.py        # ConfigManager (same INI contract)
│   └── logging.py       # QueueHandler + rotating file handler
├── gui/                 # Legacy Tkinter interface
└── ui/                  # v6 PySide6/QML interface
    ├── app.py           # Qt bootstrap and QML loader
    ├── bridge.py        # Qt properties, models, worker thread
    └── qml/             # Main window and themed components
```

Legacy import paths such as `imprint.config`, `imprint.constants`,
`imprint.events`, `imprint.math_utils`, and `imprint.logging_setup` remain
available as compatibility shims until the QML front end reaches parity.

### Design Principles

- **Thread safety** — All GUI updates routed through `self.after()` via event queues. Zero Tkinter calls from worker threads.
- **Dependency injection** — `SorterEngine` accepts a `FaceAnalyser` Protocol, enabling GPU-free unit testing with mocks.
- **Typed events** — `EngineEvent` dataclass with `EventType` enum replaces magic strings.
- **Validation** — Path overlap detection, range checking, and type validation before analysis starts.
- **Vectorised math** — `min_distance_to_references()` uses numpy matrix operations instead of Python loops.

## Development

### Prerequisites

```bash
pip install -r requirements-dev.txt
```

### Running Tests

```bash
python -m pytest tests/ -v
```

### Running with Coverage

```bash
python -m pytest tests/ --cov=imprint --cov-report=term-missing
```

### Linting

```bash
ruff check src/imprint/ tests/
```

## Packaging (Windows)

The v6 Windows bundle is built with PyInstaller and wrapped in an Inno Setup installer.

```bash
# One-time setup
pip install -r requirements-build.txt
winget install --id JRSoftware.InnoSetup -e

# Optional: prefetch the InsightFace model packs
python scripts/prefetch_models.py

# Build the one-directory application
powershell -ExecutionPolicy Bypass -File scripts/build_app.ps1

# Build the installer
powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
```

Outputs:

- `dist/Imprint/Imprint.exe` — one-directory application bundle
- `dist/installer/Imprint-6.0.0-Setup.exe` — per-user installer (no administrator rights required)

The packaging job also runs in GitHub Actions via `.github/workflows/package.yml`.
The packaged app accepts `--self-test`, which imports the critical runtime pieces and
returns a non-zero exit code if the bundle is incomplete.

The PyInstaller spec prunes unused Qt Quick style DLLs and unused Python packages,
reducing the unpacked application by roughly 38 MB and the installer by roughly 21 MB
(565 MB -> 544 MB) while preserving the full feature set.

> **Python 3.12 note:** InsightFace 0.7.3 publishes no cp312 wheel. The repository vendors
> a locally built Windows wheel in `wheelhouse/` (MinGW-w64, runtime DLLs bundled), so the
> application and packaging builds do not require a compiler. See
> [`wheelhouse/README.md`](wheelhouse/README.md) for provenance and rebuild steps.
>
> The Python 3.12 lockfile passes `pip-audit -r requirements.lock`.

## Performance

The pipeline benchmark uses a deterministic fake analyser, so it measures decoding,
copying, cache, and orchestration overhead without requiring a GPU:

```bash
python scripts/benchmark_engine.py --images 1000 --inference-ms 2
```

Sample development-machine result with 1,000 generated images:

```text
Legacy engine:        3.697s
v6 cold cache:        4.000s
v6 warm cache:        0.978s (1000 cache hits)
Cache speedup:        4.09x
Python peak memory:   2.5 MiB
```

With larger 256x256 images the overlapped decoder also beats the sequential v5
pipeline on a cold run (1.181s versus 1.358s for 300 images).

## Project Files

| File | Purpose |
|---|---|
| `run.py` | Entry point for `start.bat`; QML by default, `--legacy` for Tkinter |
| `start.bat` | Smart Windows launcher with auto-setup |
| `pyproject.toml` | Modern Python packaging metadata |
| `requirements.txt` | Pinned production dependencies |
| `requirements-dev.txt` | Development/test dependencies |
| `requirements-build.txt` | Packaging dependencies (PyInstaller) |
| `wheelhouse/` | Vendored cp312 InsightFace wheel and provenance |
| `packaging/` | PyInstaller spec, icon, version info, Inno Setup script |
| `scripts/` | Build, installer, and model-prefetch scripts |
| `.gitignore` | Excludes venv, config, caches, logs |
| [`decisions.md`](decisions.md) | Architectural & testing decisions rationale |

## Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.12 |
| **Face Analysis** | InsightFace |
| **GPU Runtime** | ONNX Runtime (CUDA) |
| **GUI** | PySide6 6 + QML (v6), Tkinter + ttk (legacy) |
| **Image I/O** | OpenCV |
| **Math** | NumPy, SciPy |
| **Testing** | pytest |
| **Packaging** | setuptools + pyproject.toml |

## License

MIT
