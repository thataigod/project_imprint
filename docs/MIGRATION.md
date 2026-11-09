# Migrating from Imprint v5

## Interface

Imprint v6 is a PySide6/QML desktop application. The legacy Tkinter interface and
the `--legacy` switch have been removed. Launch the application with:

```powershell
python run.py
```

or double-click `start.bat`.

## Python

The application now requires Python 3.12. The Windows installer bundles the runtime,
so end users do not need Python installed.

## Configuration

v5 stored `config.ini` next to the application. v6 stores it per user at:

```text
%LOCALAPPDATA%\Imprint\Imprint Face Sorter\config.ini
```

To keep v5 settings, copy the old `config.ini` to that location before first launch,
or re-enter the settings in the QML interface. The INI keys are unchanged:

- `[Paths]` — `reference_folder`, `source_folder`, `destination_folder`
- `[Settings]` — `model_name`, `distance_threshold`, `confidence_threshold`,
  `batch_size`, `number_of_subfolders`, `cache_enabled`

Logs are written to `%LOCALAPPDATA%\Imprint\Imprint Face Sorter\logs\imprint.log`.

## Models and cache

InsightFace model packs still download to `%USERPROFILE%\.insightface`. The optional
embedding cache is stored at `%USERPROFILE%\.imprint\embeddings.sqlite3` and is enabled
by default; disable it in the Settings panel if desired.

## Destination layout

The output contract is unchanged: matches are copied into
`Score_<lower>_to_<upper>` subfolders, and duplicate filenames receive `_1`, `_2`
suffixes.

## Requirements

Install the CUDA 12.x toolkit and cuDNN 9.x runtime on GPU machines. The packaged
application does not bundle those NVIDIA runtimes.
