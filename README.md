# Imprint GPU Face Sorter

A high-performance, GPU-accelerated desktop application for sorting images based on facial similarity. Powered by state-of-the-art face recognition models, Imprint automatically identifies faces in your photos and organises them into scored subdirectories with a single click.

## Features

- **State-of-the-Art Recognition** — Choose from multiple InsightFace models: *Antelope v2* (maximum accuracy), *Buffalo L* (balanced), or *Buffalo S* (fastest).
- **Automated Reference Pruning** — Provide multiple reference photos and the app intelligently finds the most consistent "core" group using a medoid-based algorithm, discarding outliers like blurry shots or side profiles.
- **User-Friendly GUI** — A clean Tkinter interface with model selection, real-time progress, a dark-themed live log, and inline tooltips on every setting.
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
| **Python** | 3.9 or later, added to PATH |
| **CUDA Toolkit** | Version 11.x (11.8 recommended) |
| **cuDNN** | v8.9.x for CUDA 11.x |

## Setup & Installation

### 1. Install CUDA and cuDNN (one-time)

1. Install the [NVIDIA CUDA Toolkit v11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive) using the "Express" option.
2. Download [cuDNN v8.9.7 for CUDA 11.x](https://developer.nvidia.com/rdp/cudnn-archive).
3. Unzip cuDNN and copy the contents of `bin/`, `include/`, and `lib/` into your CUDA installation directory (e.g. `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8`).

### 2. Download the Project

Place all project files into a new folder:

```
project_imprint/
├── start.bat
├── run.py
├── requirements.txt
├── imprint/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── constants.py
│   ├── engine.py
│   ├── events.py
│   ├── logging_setup.py
│   ├── math_utils.py
│   └── gui/
│       ├── __init__.py
│       ├── app.py
│       ├── tooltips.py
│       └── widgets.py
└── tests/
    └── ...
```

### 3. Launch

Double-click **`start.bat`**. On first run it will:
1. Check for Python ≥ 3.9
2. Create a virtual environment (`imprint_env/`)
3. Install all dependencies from `requirements.txt`

Subsequent launches skip straight to the application.

## Usage

1. **Select Folders**
   - **Reference Folder** — Multiple clear photos of the face you want to find.
   - **Source Folder** — All images to sort through (searched recursively).
   - **Destination Folder** — Where matched images are copied.

2. **Configure Settings**
   - Select a **Recognition Model** — this auto-populates recommended threshold and batch size.
   - Adjust **Distance Threshold** (lower = stricter), **Face Confidence** (0.0–1.0), **Batch Size**, and **Number of Subfolders** as needed.
   - Hover over any setting for a tooltip explanation.

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
imprint/
├── __init__.py          # Package metadata and version
├── __main__.py          # python -m imprint entry point
├── constants.py         # Named constants, model registry
├── config.py            # ConfigManager with typed dataclasses + validation
├── engine.py            # SorterEngine with Protocol-based DI
├── events.py            # Typed event system (Enum + dataclass)
├── logging_setup.py     # QueueHandler + rotating file handler
├── math_utils.py        # Vectorised cosine distance functions
└── gui/
    ├── __init__.py
    ├── app.py           # Main Application window
    ├── tooltips.py      # ToolTip widget
    └── widgets.py       # PathSelector, SettingEntry, ModelSelector
```

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
ruff check imprint/ tests/
```

## Project Files

| File | Purpose |
|---|---|
| `run.py` | Convenience entry point for `start.bat` |
| `start.bat` | Smart Windows launcher with auto-setup |
| `pyproject.toml` | Modern Python packaging metadata |
| `requirements.txt` | Pinned production dependencies |
| `requirements-dev.txt` | Development/test dependencies |
| `.gitignore` | Excludes venv, config, caches, logs |
| [`decisions.md`](decisions.md) | Architectural & testing decisions rationale |

## Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.9+ |
| **Face Analysis** | InsightFace |
| **GPU Runtime** | ONNX Runtime (CUDA) |
| **GUI** | Tkinter + ttk |
| **Image I/O** | OpenCV |
| **Math** | NumPy, SciPy |
| **Testing** | pytest |
| **Packaging** | setuptools + pyproject.toml |

## License

MIT
