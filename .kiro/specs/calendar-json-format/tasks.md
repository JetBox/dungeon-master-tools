# Implementation Plan: calendar-json-format

## Overview

Extracts the Gregorian calendar into a JSON asset, adds a `calendar_source` field to `Project`, introduces `CalendarLoader`, updates `Serializer.load`, and wires in `CalendarSelectorDialog` so new project creation is driven by user choice rather than a hardcoded default.

## Tasks

- [x] 1. Create `assets/calendars/gregorian.json`
  - Create the `assets/calendars/` directory and write the full Gregorian calendar definition as JSON, mirroring the schema produced by `Serializer.save()` for the `calendar_definition` block
  - Include all fields: `name`, `months` (with `leap_every_n_years`), `week_length`, `weekday_names`, `hours_per_day`, `week_start_offset`, `lunar_cycles`, `intercalary_periods`, `eras`
  - _Requirements: 1.1, 1.3_

- [x] 2. Add `calendar_source` field to `Project`
  - [x] 2.1 Add `calendar_source: str = ""` as the last field of the `Project` dataclass in `src/models.py`
    - _Requirements: 6.1, 6.2, 6.5_

  - [ ]* 2.2 Write property test for `calendar_source` round-trip
    - **Property 6: calendar_source round-trip**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.5**

- [x] 3. Create `src/calendar_loader.py`
  - [x] 3.1 Implement `load_calendar_file(path: str) -> CalendarDefinition`
    - Define `CALENDAR_REQUIRED_FIELDS = ("name", "months", "week_length", "weekday_names", "hours_per_day")`
    - Open `path`; raise `ProjectLoadError("Calendar file not found: {path}")` on `FileNotFoundError`
    - Parse JSON; raise `ProjectLoadError("Invalid JSON in calendar file: {e}")` on `JSONDecodeError`
    - Check each required field; raise `ProjectLoadError("Missing required calendar field: '{field}'")`  if absent
    - Delegate to `_load_calendar_definition(data)` imported from `src.serializer`; propagate any `ProjectLoadError`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 3.2 Write property test — valid calendar JSON always loads without error
    - **Property 2: Valid calendar JSON always loads without error**
    - **Validates: Requirements 2.2**

  - [ ]* 3.3 Write property test — missing required field always raises ProjectLoadError
    - **Property 3: Missing required field always raises ProjectLoadError**
    - **Validates: Requirements 2.5, 2.6**

- [x] 4. Update `Serializer.load` to read `calendar_source`
  - In `src/serializer.py`, add `calendar_source=data.get("calendar_source", "")` to the `Project(...)` constructor call inside `Serializer.load`
  - No changes needed to `Serializer.save` — `dataclasses.asdict` will include the new field automatically
  - _Requirements: 4.2, 4.3, 6.3, 6.4_

  - [ ]* 4.1 Write property test — Serializer embeds full `calendar_definition` on save
    - **Property 4: Serializer embeds full calendar_definition on save**
    - **Validates: Requirements 4.1**

  - [ ]* 4.2 Write property test — Project serialization round-trip preserves CalendarDefinition
    - **Property 5: Project serialization round-trip preserves CalendarDefinition**
    - **Validates: Requirements 4.2**

- [x] 5. Create `src/views/calendar_selector_dialog.py`
  - [x] 5.1 Implement `CalendarSelectorDialog(QDialog)`
    - Layout: `QLabel` prompt, "Load from File" `QPushButton`, "Generate Fantasy Calendar" `QPushButton`, hidden red `QLabel` for errors, `QDialogButtonBox` with Cancel only
    - "Load from File" → `QFileDialog.getOpenFileName` filtered to `*.json` → call `load_calendar_file(path)`; on `ProjectLoadError` show error label and stay open; on success store result and call `self.accept()`
    - "Generate Fantasy Calendar" → store stub `CalendarDefinition(name="Fantasy Calendar", months=[MonthDefinition("Month 1", 30)], week_length=7, weekday_names=["Day 1"…"Day 7"], hours_per_day=24)` and call `self.accept()`
    - Cancel → `self.reject()`
    - Implement `get_calendar(self) -> CalendarDefinition | None` returning the stored result or `None`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 6. Update `AppController.on_new_project` to use `CalendarSelectorDialog`
  - In `src/controller.py`, replace the hardcoded `GREGORIAN_DEFAULT` assignment with the two-step flow: `ProjectDialog` → `CalendarSelectorDialog`
  - Set `calendar_source=calendar.name` when constructing the new `Project`
  - Remove the now-unused `GREGORIAN_DEFAULT` import from `src/controller.py` (the constant stays in `models.py` for `Serializer.load` fallback)
  - _Requirements: 3.1, 3.3, 3.4, 3.5, 5.1, 5.2, 5.3, 6.1, 6.2_

- [x] 7. Checkpoint — verify everything works together
  - Ensure all tests pass, ask the user if questions arise.
  - Smoke-check: load `assets/calendars/gregorian.json` via `load_calendar_file` and assert the result equals `GREGORIAN_DEFAULT`
  - Smoke-check: create a new project via the UI, choose "Load from File" with `gregorian.json`, save, reload, and verify the calendar and `calendar_source` are intact

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- `GREGORIAN_DEFAULT` remains in `models.py` as a fallback for `Serializer.load()` on old project files — do not remove it
- Property tests use Hypothesis; tag format: `# Feature: calendar-json-format, Property {N}: {property_text}`
