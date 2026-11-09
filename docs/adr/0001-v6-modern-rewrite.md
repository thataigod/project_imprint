# ADR 0001: Imprint v6 Modern Desktop Rewrite

- **Status:** Accepted
- **Date:** 2026-11-08
- **Branch:** `feat/v6-modern-ui`

## Context

Imprint v5 is a working Python 3.9+ desktop application built with Tkinter. It
sorts images by facial similarity using InsightFace embeddings, a medoid-based
reference-pruning algorithm, cosine distance, and score-tiered destination
folders. The engine is well tested and intentionally isolated from the GUI, but
the Tkinter interface looks dated and the sequential inference pipeline leaves
GPU capacity unused.

The goal is to deliver the same user-facing workflow with a modern, advanced
interface and a faster, more maintainable runtime without changing the meaning
of existing settings or the output layout.

## Decision

Rebuild the application around:

| Concern | Decision |
|---|---|
| UI | PySide6 6.8+ with QML/Qt Quick Controls, dark and light themes |
| Language/runtime | Python 3.12 managed by `uv` |
| Inference | InsightFace with ONNX Runtime 1.20 (CUDA 12 / cuDNN 9), DirectML and CPU fallbacks |
| Settings | Pydantic Settings reading and writing the existing `config.ini` keys |
| Engine/UI bridge | Qt signals from a worker `QThread`; engine remains UI-agnostic via typed events |
| Logging | structlog plus rotating file output and an in-app console drawer |
| Packaging | PyInstaller or Nuitka onedir build with an Inno Setup installer |
| Repository layout | `src/` layout with domain, engine, events, platform, and ui packages |
| Quality gates | pytest, pytest-qt, hypothesis, ruff, strict mypy, pip-audit, 100% core coverage |

### Scope

Functional parity is mandatory. The following behaviours must not change:

- Three folder inputs: reference, source, and destination.
- Recursive source-image discovery for the existing supported extensions.
- The `antelopev2`, `buffalo_l`, and `buffalo_s` model registry, including
  recommended threshold and batch-size auto-fill.
- Distance threshold, face confidence, batch size, and subfolder-count settings.
- Reference selection: best face per image by detection score, medoid chosen by
  minimum total cosine distance, outliers pruned at the distance threshold.
- Matching: best detected face per source image, minimum cosine distance to the
  core reference set, match when distance is at or below the threshold.
- Destination layout: `Score_<lower>_to_<upper>` directories and `_N` suffixes
  for duplicate filenames.
- Cancellation, live progress/logging, validation messages, and `config.ini`
  persistence.

The following enhancements are explicitly in scope but must be additive and
must not alter the output of a run:

- SQLite embedding cache keyed by path, modification time, size, and model.
- Streaming result thumbnails with face crops and score badges.
- ETA, live match/skip/error counts, and a richer summary dashboard.
- Pause and resume in addition to cancel.
- CSV manifest export of matched images.
- Dark/light themes, drag-and-drop folders, HiDPI support, and keyboard shortcuts.

### Non-goals

- Changing recognition models or the matching algorithm.
- Cloud processing or telemetry.
- Cross-platform packaging in the first release; Windows 10/11 remains the target.

## Architecture

```
src/imprint/
├── domain/      # constants, model registry, settings models, math
├── engine/      # analyser protocol, reference pruning, pipeline, sorter, cache
├── events/      # typed engine events
├── platform/    # config persistence, logging, model prefetch
├── ui/          # QML views, view models, Qt bridge
tests/
├── unit/        # pure logic, 100% coverage
├── parity/      # legacy versus new engine comparison
└── ui/          # pytest-qt interaction tests
```

The legacy Tkinter UI has been removed. Thin compatibility modules keep the
historical `imprint.*` import paths available for downstream integrations, while
the v5 engine remains as a parity and benchmark fixture.

## Migration Plan

0. Branch, ADR, pinned CUDA/cuDNN/ONNX Runtime matrix, parity checklist.
1. `src/` scaffold; port constants, settings, events, and math with tests.
2. New engine pipeline, analyser protocol, batching, cache, and parity harness.
3. QML shell, folder workflow, settings, live results, summary, and log drawer.
4. PyInstaller build, Inno Setup installer, model prefetch, packaged-app self-test.
5. Python 3.12, audit, benchmarks, bundle trimming, docs, legacy UI removal.

## Implementation Status

- **Phase 0** complete: ADR, stack decisions, and parity scope approved.
- **Phase 1** complete: `src/` layout, domain/events/platform packages, shims, and tooling.
- **Phase 2** complete: `EngineV6`, overlapped decoding, SQLite cache, pause/cancel,
  rich events, and a legacy-versus-v6 parity harness.
- **Phase 3** complete: PySide6/QML interface, Qt bridge, live results grid, settings,
  drag-and-drop folder cards, activity log, summary, themes, and worker lifecycle.
  The QML interface is launchable with `python run.py`.
- **Phase 4** complete: the QML interface became the default entry point while
  `--legacy` retained the Tkinter interface during the transition. Existing
  `config.ini` files are loaded directly by the Qt bridge.
- **Phase 5** complete: the runtime is Python 3.12, the lockfile is regenerated
  and passes `pip-audit`, and the PyInstaller one-directory build plus per-user
  Inno Setup installer are verified. InsightFace 0.7.3 has no cp312 wheel, so a
  MinGW-w64-built wheel with bundled runtime DLLs is vendored in `wheelhouse/`;
  packaging does not require a C++ toolchain.
- **Phase 6** complete: pipeline and cache benchmarks are automated; committed
  SQLite writes improved cold-cache overhead; 1,000-image and 300-image stress
  runs pass; the bundled app has a `--self-test` gate; unused Qt styles and
  packages are pruned (~38 MB unpacked / ~21 MB installer); and the security audit
  is clean.
- **Phase 7** complete: the Tkinter interface and `--legacy` switch are removed,
  release documentation and the changelog are written, and the final package and
  installer are verified. The final unpacked bundle is about 1.60 GB and the
  per-user installer is about 542 MB.

## Verification

- A parity harness runs the legacy and new engines over the same fixture set and
  asserts identical match decisions, scores, subfolder names, and copied files.
- Engine tests use the `FaceAnalyser` protocol and require no GPU.
- UI tests run under pytest-qt with the offscreen Qt platform.
- CI runs ruff, mypy, pip-audit, and pytest on Windows and Linux.
- A manual GPU smoke test covers model download, warm-up, cancellation, pause,
  duplicate names, and destination opening.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| CUDA, cuDNN, and ONNX Runtime incompatibility | Pin a known-good matrix and keep DirectML/CPU fallbacks |
| Silent behaviour drift | Mandatory legacy-versus-new parity harness |
| Large installer size | Onedir build, compression, models downloaded outside the installer |
| Qt packaging complexity | Keep QML resources in a Qt resource file and test the frozen build early |
| GUI test fragility | pytest-qt with offscreen platform; keep engine tests GPU-free |
| Config compatibility | Reuse the existing INI keys and add a round-trip regression test |
