# Project Imprint Architectural & Testing Decisions

This document outlines the key technical decisions taken during the rebuild and enhancement of **Project Imprint (v5)**, documenting the rationale behind each choice for future developers and AI agents.

---

## 1. Thread Separation (Responsive GUI vs. Background Engine)
*   **Decision**: All heavy processing (InsightFace GPU execution, image reading, math computations, and file system writes) runs on a background `SorterEngine` thread, while the main thread manages the Tkinter GUI.
*   **Why**: standard Tkinter is single-threaded and blocks/freezes (rendering the OS window "Not Responding") when doing blocking calculations. A queue-based asynchronous architecture keeps the interface fully responsive.
*   **Communication Contract**: The background thread communicates with the main thread using a frozen dataclass `EngineEvent` containing typed enums (`EventType`, `MessageLevel`), ensuring safe, type-verified boundaries across threads.

---

## 2. List-Based File Discovery vs. Generators
*   **Decision**: `SorterEngine._discover_images` recursively scans directories and returns a sorted `list[Path]` instead of a lazy generator.
*   **Why**:
    1. **Progress Accuracy**: The GUI requires the total file count upfront to estimate progress percentages (e.g. `Batch X/Y`, `Z% complete`). Generators do not support length checks.
    2. **Deterministic Processing**: Images must be processed in sorted, alphabetical order to ensure reproducibility and ease of debugging. Sorting an iterator requires loading the entire collection into memory anyway.
    3. **Resource Context**: The memory overhead of storing 100k paths in a list (~15MB) is completely negligible compared to the ONNX/InsightFace runtime (>500MB). Using a generator yields zero meaningful resource benefits in this context.

---

## 3. Optional `scipy` Dependency & NumPy Fallback
*   **Decision**: The dependency on `scipy` has been made optional. A pure-NumPy vectorized fallback is implemented in `math_utils.py` to compute cosine distance matrices if `scipy` is absent.
*   **Why**: To support lightweight and error-free deployments in environments where compiling/installing SciPy is slow or restricted, while still utilizing SciPy's optimized `cdist` when available.

---

## 4. Single Python/OS Target in CI Pipeline
*   **Decision**: The GitHub Actions CI configuration is restricted to Python 3.10 on Ubuntu, utilizing `xvfb-run` for headless GUI execution.
*   **Why**: Restricting the build matrix prevents long download and compilation times (especially on Windows/macOS runners which do not compile ONNX/InsightFace binaries out of the box). This keeps build durations under 90 seconds, maintaining a fast feedback loop for develop/master commits.

---

## 5. Dynamic Headless Test Skipping & Session-Scoped Root
*   **Decision**: GUI-related tests are automatically skipped if no graphical display is present, checked via a custom `check_display()` hook in `conftest.py` that keeps a single, session-scoped `tk.Tk` root window alive.
*   **Why**:
    1. **Portability**: Allows running unit tests in headless environments (e.g., Docker, SSH sessions) without crashing on missing display errors.
    2. **Windows Library Path Bug**: Instantiating and destroying multiple `tk.Tk` windows in a single test process causes Tcl/Tk path caching to break on Windows (raising `TclError: invalid command name "tcl_findLibrary"`). Keeping a single verification root window alive avoids this platform bug.

---

## 6. Graceful Tkinter Startup Checks
*   **Decision**: Catch `TclError` and `ImportError` in `imprint/__main__.py` and print a user-friendly CLI troubleshooting guide to standard error, exiting with code 1 instead of exposing a raw Python stack trace.
*   **Why**: Guides non-technical users immediately when they attempt to run the app in an environment lacking graphical desktop servers (X11/Wayland/Windows Desktop) or Tcl/Tk installations.

---

## 7. Pragma-Ignored Low-Level Exception Paths in Testing
*   **Decision**: Maintain a strict 100% test coverage target in CI, but allow `# pragma: no cover` on low-level, system-dependent error-handling blocks.
*   **Why**: Simulating low-level platform errors (such as C-level ONNX GPU failures, corrupted image file descriptors, or disk-write blocks) in Python unit tests requires complex mocking layers. The overhead of writing and maintaining these mocks is disproportionately high compared to the negligible safety they add.

---

## 8. Static Type-Checking with Mypy
*   **Decision**: Integrate `mypy` with a strict configuration (`disallow_untyped_defs`, `disallow_incomplete_defs`, `warn_return_any`) into the development workflow and CI pipeline.
*   **Why**: Since the codebase handles complex multi-threaded flow, dependency-injected interfaces (e.g. `FaceAnalyser`), and numpy arrays/matrices, type annotations are critical for preventing runtime type mismatches. Using `mypy` ensures these type annotations are verified automatically on every commit.

---

## 9. Windows pytest stdout redirection bug and the `-s` flag
*   **Decision**: For local test runs on Windows, the `-s` flag (no stdout/stderr capture, e.g. `pytest tests/ --cov=imprint -s`) must be used.
*   **Why**: Standard pytest runs capture standard streams, which can corrupt file descriptor references in Windows Tkinter/Tcl handles during repeated setup/teardowns, leading to initialization crashes. Running without capture (-s) resolves this platform-specific friction.

---

## 10. `TclError` String Comparison in App Startup
*   **Decision**: In `imprint/__main__.py`, we catch startup exceptions and check if `type(exc).__name__ == "TclError"`.
*   **Why**: Importing `tkinter.TclError` at the module level would defeat the purpose of the lazy import inside the `try` block, as `tkinter` itself might not be importable (for example, on headless systems or installations without Tk). Therefore, comparing the exception's class name string is the most robust way to identify `TclError` without needing a pre-emptive import of `tkinter`.

