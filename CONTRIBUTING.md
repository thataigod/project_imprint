# Contributing to Project Imprint

Thank you for contributing to **Project Imprint**! To maintain code quality, type safety, and comprehensive test coverage, please follow the guidelines below.

---

## 1. Development Environment Setup

This project is built using Python 3.10. Ensure you have the recommended environment setup:

1. **Create the virtual environment**:
   ```bash
   python -m venv imprint_env
   ```
2. **Activate the environment**:
   * **Windows**: `imprint_env\Scripts\activate.bat` (cmd) or `.\imprint_env\Scripts\Activate.ps1` (PowerShell)
   * **Linux/macOS**: `source imprint_env/bin/activate`
3. **Install dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. **Set up pre-commit hooks**:
   ```bash
   pre-commit install
   ```

---

## 2. Coding Standards & Tooling

We enforce strict linting, formatting, and static typing:
* **Linting & Formatting**: We use `ruff`. Run it locally via:
  ```bash
  ruff check imprint/ tests/
  ruff format imprint/ tests/
  ```
* **Static Typing**: We use `mypy` with strict configuration parameters. Run it locally via:
  ```bash
  mypy imprint/
  ```

Pre-commit hooks will automatically run `ruff` and `mypy` on files modified during commit.

---

## 3. Testing Guidelines

We enforce a **100% test coverage target** in the CI pipeline.

* **Running Tests Locally**:
  ```bash
  pytest tests/ -v
  ```
* **Running Tests with Coverage**:
  ```bash
  pytest tests/ --cov=imprint --cov-fail-under=100
  ```

### Platform-Specific Testing Rules

> [!IMPORTANT]
> **Windows stdout/stderr Capture Bug**:
> Standard pytest runs capture standard streams, which can corrupt file descriptor references in Windows Tkinter/Tcl handles during repeated setup/teardowns, leading to initialization crashes.
> 
> When running pytest locally on Windows, you **MUST** pass the `-s` flag to disable stdout/stderr capture:
> ```bash
> pytest tests/ --cov=imprint --cov-fail-under=100 -s
> ```

---

## 4. Pull Request & Deployment Flow

1. All new feature development, documentation updates, and bug fixes must target the `develop` branch.
2. Verify that local unit tests, type checks (`mypy`), and linter passes before pushing.
3. The GitHub Actions CI pipeline executes `ruff`, `mypy`, `pip-audit`, and `pytest` (using `xvfb-run` for headless GUI execution on Linux).
4. Once the CI pipeline on the `develop` branch passes successfully, the code can be merged into `master`.
