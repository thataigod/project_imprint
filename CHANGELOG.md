# Changelog

All notable changes to Imprint are documented here.

## [6.0.0] - 2026-11-09

### Added

- Modern PySide6 6 / QML desktop interface with dark and light themes.
- Drag-and-drop folder cards, live result grid, filters, activity log, summary
  dashboard, and inline setting help.
- Full-image result viewer with left/right arrow navigation inside the active
  result filter.
- Matches-only result filter is selected by default.
- Overlapped decoding pipeline with optional SQLite embedding cache.
- Pause/resume and graceful cancellation across the worker lifecycle.
- CSV-ready run summaries and streaming per-image results.
- Per-user Windows installer and packaged one-directory application.
- `Imprint.exe --self-test` bundle verification gate.
- Engine benchmark, cache benchmark, and large-folder stress tooling.
- Vendored cp312 InsightFace wheel built with MinGW-w64.
- GitHub Actions CI for tests, linting, typing, audit, and packaging.

### Changed

- Runtime upgraded to Python 3.12.
- Configuration and logs now live in per-user AppData locations.
- QML resources and Windows version metadata are bundled into the application.
- ONNX Runtime pinned to CUDA 12 / cuDNN 9 compatible releases.
- Source image totals now display correctly while an analysis is running.
- Lockfile updated; `pip-audit` reports no known vulnerabilities.
- Bundle pruned by removing unused Qt Quick styles and packages.

### Removed

- Legacy Tkinter interface and the `--legacy` launcher switch.
- Tkinter-specific widgets, tooltips, tests, and launcher setup.

### Verification

- 100% test coverage on core and UI Python modules.
- Legacy-versus-v6 engine parity harness passes.
- Race, cancellation, duplicate-name, corrupt-image, and path-traversal paths covered.
- Installer install, launch, self-test, and uninstall verified on Windows.
