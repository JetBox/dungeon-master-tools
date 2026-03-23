# Implementation Plan: TTRPG DM Tool

## Overview

Implement the core application shell in Python/PyQt6: a resizable main window with a tabbed interface, a File menu, and project create/save/load functionality backed by JSON serialization.

## Tasks

- [x] 1. Set up project structure and core model
  - Create `src/` directory with `__init__.py`, `models.py`, `errors.py`
  - Define the `Project` dataclass with `name: str` and `version: str = "1.0"`
  - Define `ProjectLoadError(Exception)` in `errors.py`
  - Create `main.py` entry point that constructs `QApplication` and starts the event loop
  - Add `requirements.txt` with `PyQt6` and `hypothesis`
  - _Requirements: 7.1, 7.2_

- [x] 2. Implement Serializer
  - [x] 2.1 Implement `Serializer` class in `src/serializer.py`
    - `save(project, path)` writes pretty-printed JSON (4-space indent) atomically (write to temp file, then replace)
    - `load(path)` reads JSON, validates required fields (`name`, `version`), raises `ProjectLoadError` with field name on missing field
    - _Requirements: 5.1, 5.3, 5.4, 6.2, 7.1, 7.2, 7.4_

  - [ ]* 2.2 Write property test for serialization round-trip (Property 6)
    - `# Feature: ttrpg-dm-tool, Property 6: Serialization round-trip`
    - Generate arbitrary `Project` instances via Hypothesis `@given`; serialize to temp file, deserialize, assert equality
    - `@settings(max_examples=100)`
    - **Property 6: Serialization round-trip**
    - **Validates: Requirements 7.3, 7.2, 5.1, 6.2**

  - [ ]* 2.3 Write property test for valid pretty-printed JSON output (Property 7)
    - `# Feature: ttrpg-dm-tool, Property 7: Serialized output is valid, pretty-printed JSON containing required fields`
    - Generate arbitrary `Project` instances; serialize and assert `json.loads` succeeds, output contains newline, `name` and `version` fields match
    - `@settings(max_examples=100)`
    - **Property 7: Serialized output is valid, pretty-printed JSON containing required fields**
    - **Validates: Requirements 5.3, 7.1**

  - [ ]* 2.4 Write property test for missing required field error (Property 8)
    - `# Feature: ttrpg-dm-tool, Property 8: Missing required field raises descriptive error`
    - For each required field (`name`, `version`), generate valid projects, remove field from serialized JSON, assert `ProjectLoadError` message contains the field name
    - `@settings(max_examples=100)`
    - **Property 8: Missing required field raises descriptive error**
    - **Validates: Requirements 7.4**

  - [ ]* 2.5 Write unit tests for Serializer error paths
    - Test `load` with malformed JSON raises `ProjectLoadError`
    - Test `save` propagates `OSError` on write failure
    - _Requirements: 5.4, 6.4, 6.5_

- [x] 3. Checkpoint — Ensure all Serializer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement MainWindow and ProjectDialog views
  - [x] 4.1 Implement `MainWindow` in `src/views/main_window.py`
    - Subclass `QMainWindow`; set default size 1024×768 and minimum size 640×480
    - Add `QMenuBar` with `File` menu containing "New Project", "Save Project", "Load Project" actions
    - Set a `QTabWidget` as the central widget with an initial "Campaign Overview" placeholder tab
    - Expose `set_title(project_name: str)` to update `setWindowTitle`
    - _Requirements: 1.1, 1.2, 2.3, 3.1, 3.3_

  - [ ]* 4.2 Write property test for tab area contained within window bounds (Property 1)
    - `# Feature: ttrpg-dm-tool, Property 1: Tab area contained within window bounds`
    - Generate random `QSize` values ≥ minimum size; resize window and assert `tab_widget.geometry()` is contained within `window.geometry()`
    - `@settings(max_examples=100)`
    - **Property 1: Tab area contained within window bounds**
    - **Validates: Requirements 2.1, 2.2**

  - [ ]* 4.3 Write property test for tab selection foregrounds correct view (Property 2)
    - `# Feature: ttrpg-dm-tool, Property 2: Tab selection foregrounds correct view`
    - Generate random tab counts (1–10) and valid indices; set `currentIndex` and assert `currentWidget()` matches the widget at that index
    - `@settings(max_examples=100)`
    - **Property 2: Tab selection foregrounds correct view**
    - **Validates: Requirements 3.2**

  - [x] 4.4 Implement `ProjectDialog` in `src/views/project_dialog.py`
    - Subclass `QDialog` with a `QLineEdit`, OK/Cancel buttons, and an inline `QLabel` for validation errors
    - On OK: if name is empty or whitespace-only, show inline error and keep dialog open; otherwise accept and expose `get_name() -> str`
    - _Requirements: 4.1, 4.3, 4.4_

  - [ ]* 4.5 Write property test for new project name preserved (Property 3)
    - `# Feature: ttrpg-dm-tool, Property 3: New project name is preserved`
    - Generate arbitrary non-empty, non-whitespace strings; simulate dialog acceptance and assert the returned name equals the input exactly
    - `@settings(max_examples=100)`
    - **Property 3: New project name is preserved**
    - **Validates: Requirements 4.2**

  - [ ]* 4.6 Write property test for whitespace names rejected (Property 4)
    - `# Feature: ttrpg-dm-tool, Property 4: Whitespace project names are rejected`
    - Generate whitespace-only strings (including empty string); assert dialog validation rejects them and does not accept
    - `@settings(max_examples=100)`
    - **Property 4: Whitespace project names are rejected**
    - **Validates: Requirements 4.3**

  - [ ]* 4.7 Write unit tests for MainWindow startup state
    - Assert window has menu bar, tab widget, and "Campaign Overview" tab on launch
    - Assert minimum size is enforced (`minimumSize()` returns ≥ 640×480)
    - _Requirements: 1.1, 1.2, 2.3, 3.1, 3.3_

- [x] 5. Checkpoint — Ensure all view tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement AppController and wire everything together
  - [x] 6.1 Implement `AppController` in `src/controller.py`
    - Constructor accepts `MainWindow` and `Serializer`; connects File menu action signals to handler slots
    - `on_new_project`: opens `ProjectDialog`; on acceptance creates `Project`, sets as active, calls `window.set_title()`
    - `on_save_project`: if no active project shows `QMessageBox.information`; otherwise opens `QFileDialog.getSaveFileName` filtered to `*.json`, calls `serializer.save`, shows `QMessageBox.critical` on `OSError`
    - `on_load_project`: opens `QFileDialog.getOpenFileName` filtered to `*.json`, calls `serializer.load`, sets active project, calls `window.set_title()`; shows `QMessageBox.critical` on `ProjectLoadError` or `OSError`
    - _Requirements: 4.1, 4.2, 4.4, 4.5, 5.1, 5.2, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 6.2 Write property test for title bar reflects active project name (Property 5)
    - `# Feature: ttrpg-dm-tool, Property 5: Title bar reflects active project name`
    - Generate arbitrary project names; simulate project creation and loading via controller, assert `window.windowTitle()` contains the project name
    - `@settings(max_examples=100)`
    - **Property 5: Title bar reflects active project name**
    - **Validates: Requirements 4.5, 6.3**

  - [ ]* 6.3 Write unit tests for AppController error and edge-case paths
    - Test save with no active project shows info message (mock `QMessageBox`)
    - Test cancel on `ProjectDialog` leaves `controller._project` as `None`
    - Test load with invalid JSON shows critical error and leaves state unchanged
    - Test file picker for load is filtered to JSON files
    - _Requirements: 4.4, 5.2, 6.1, 6.4, 6.5_

  - [x] 6.4 Wire `AppController` into `main.py`
    - Instantiate `Serializer`, `MainWindow`, and `AppController` in `main.py`; show window and start event loop
    - _Requirements: 1.1_

- [x] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `@settings(max_examples=100)` and are tagged with `# Feature: ttrpg-dm-tool, Property N: ...`
- Unit tests use pytest; run with `pytest tests/`
- The atomic save pattern (write temp → replace) in `Serializer.save` satisfies Requirement 5.4 (original file untouched on error)
