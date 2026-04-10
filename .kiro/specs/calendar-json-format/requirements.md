# Requirements Document

## Introduction

This feature moves the `GREGORIAN_DEFAULT` calendar definition out of Python source code and into a standalone JSON file on disk. It establishes a calendar JSON format that users can save, share, and load independently of any project file. The project JSON continues to embed the full calendar definition for portability, but the canonical authoring source is a `.json` file. On new project creation, the app prompts the user to either load an existing calendar JSON file or generate a new fantasy calendar (stub).

## Glossary

- **Calendar_File**: A standalone `.json` file on disk that contains a single `CalendarDefinition` serialized to JSON.
- **Calendar_Loader**: The component responsible for reading a Calendar_File from disk and deserializing it into a `CalendarDefinition` object.
- **Calendar_Selector_Dialog**: The UI dialog shown when the user creates a new project, offering the choice to load a Calendar_File or generate a new fantasy calendar.
- **CalendarDefinition**: The Python dataclass in `src/models.py` that fully describes a calendar system (months, week structure, eras, etc.).
- **Project_File**: The existing `.json` file that stores a full project, including an embedded `calendar_definition` block.
- **Serializer**: The existing class in `src/serializer.py` that reads and writes Project_Files.
- **AppController**: The existing class in `src/controller.py` that coordinates UI actions with the data model.
- **GREGORIAN_DEFAULT**: The Gregorian calendar definition, currently a Python constant in `src/models.py`, to be replaced by a bundled Calendar_File.

---

## Requirements

### Requirement 1: Gregorian Calendar Bundled as a JSON File

**User Story:** As a developer, I want the Gregorian calendar definition stored in a JSON file rather than hardcoded in Python, so that it is treated consistently with any other calendar definition.

#### Acceptance Criteria

1. THE Calendar_File `assets/calendars/gregorian.json` SHALL exist and contain a valid, complete serialization of the Gregorian calendar definition.
2. WHEN the application starts, THE Calendar_Loader SHALL be able to deserialize `assets/calendars/gregorian.json` into a `CalendarDefinition` equivalent to the current `GREGORIAN_DEFAULT` constant.
3. THE Calendar_File format SHALL use the same JSON schema already produced by `Serializer.save()` for the `calendar_definition` block within a Project_File.
4. FOR ALL valid Calendar_Files, deserializing then re-serializing then deserializing SHALL produce a `CalendarDefinition` equal to the original (round-trip property).

---

### Requirement 2: Standalone Calendar File Loading

**User Story:** As a user, I want to load a calendar definition from a standalone JSON file, so that I can reuse the same calendar across multiple projects without redefining it each time.

#### Acceptance Criteria

1. THE Calendar_Loader SHALL expose a function that accepts a file path and returns a `CalendarDefinition`.
2. WHEN a file at the given path contains valid calendar JSON, THE Calendar_Loader SHALL return the corresponding `CalendarDefinition` without error.
3. IF the file at the given path does not exist, THEN THE Calendar_Loader SHALL raise a `ProjectLoadError` with a descriptive message.
4. IF the file at the given path contains malformed JSON, THEN THE Calendar_Loader SHALL raise a `ProjectLoadError` with a descriptive message.
5. IF the file at the given path contains JSON that is missing required calendar fields, THEN THE Calendar_Loader SHALL raise a `ProjectLoadError` with a descriptive message.
6. WHEN a Calendar_File is read from disk, THE Calendar_Loader SHALL validate that the parsed JSON contains the required top-level calendar fields (`name`, `months`, `week_length`, `weekday_names`, `hours_per_day`) before attempting deserialization, and IF any required field is absent, THEN THE Calendar_Loader SHALL raise a `ProjectLoadError` with a message identifying the missing field.
7. THE Calendar_Loader SHALL reuse the existing `_load_calendar_definition(data: dict)` logic in `src/serializer.py` to perform deserialization.

---

### Requirement 3: New Project Calendar Selection

**User Story:** As a user, I want to choose a calendar when creating a new project, so that I am not silently assigned the Gregorian calendar by default.

#### Acceptance Criteria

1. WHEN the user triggers "New Project", THE Calendar_Selector_Dialog SHALL be presented before the project is created.
2. THE Calendar_Selector_Dialog SHALL offer two options: "Load Calendar from File" and "Generate Fantasy Calendar".
3. WHEN the user selects "Load Calendar from File" and confirms a valid Calendar_File, THE AppController SHALL create the new project using the `CalendarDefinition` loaded from that file.
4. WHEN the user selects "Generate Fantasy Calendar", THE AppController SHALL create the new project using a stub `CalendarDefinition` (placeholder implementation; full generation is out of scope).
5. IF the user dismisses the Calendar_Selector_Dialog without making a selection, THEN THE AppController SHALL cancel new project creation and leave the application state unchanged.
6. IF the user selects "Load Calendar from File" and the selected file fails to load, THEN THE Calendar_Selector_Dialog SHALL display an error message and remain open so the user can select a different file.

---

### Requirement 4: Project File Continues to Embed Calendar Definition

**User Story:** As a user, I want my saved project file to remain self-contained, so that I can share or move it without needing to distribute a separate calendar file.

#### Acceptance Criteria

1. WHEN the `Serializer` saves a project, THE Serializer SHALL embed the full `calendar_definition` block inline in the Project_File, regardless of whether the calendar originated from a Calendar_File or a stub.
2. WHEN the `Serializer` loads a Project_File that contains a `calendar_definition` block, THE Serializer SHALL reconstruct the `CalendarDefinition` from that embedded block without requiring a separate Calendar_File on disk.
3. THE Project_File format SHALL remain backward-compatible with existing saved projects that already contain an embedded `calendar_definition` block.

---

### Requirement 6: Project Saves Calendar Source Alongside Tracked Date

**User Story:** As a user, I want my saved project to record which calendar was in use, so that when the project is loaded I can see or reference the calendar name without inspecting the full embedded definition.

#### Acceptance Criteria

1. WHEN the `Serializer` saves a project that has a `tracked_date`, THE Serializer SHALL include a `calendar_source` field in the Project_File containing the `name` of the active `CalendarDefinition`.
2. WHEN the `Serializer` saves a project that has no `tracked_date`, THE Serializer SHALL still include the `calendar_source` field reflecting the active `CalendarDefinition` name.
3. WHEN the `Serializer` loads a Project_File that contains a `calendar_source` field, THE Serializer SHALL make the value available on the loaded `Project` object.
4. IF a Project_File does not contain a `calendar_source` field, THEN THE Serializer SHALL load the project without error, treating `calendar_source` as absent (backward-compatibility).
5. THE `calendar_source` field SHALL be a plain string equal to the `CalendarDefinition.name` value at the time of saving.

---

### Requirement 5: Remove GREGORIAN_DEFAULT Hardcoding from AppController

**User Story:** As a developer, I want `AppController.on_new_project()` to stop hardcoding `GREGORIAN_DEFAULT`, so that the calendar selection is always driven by user input.

#### Acceptance Criteria

1. THE AppController SHALL obtain the `CalendarDefinition` for a new project exclusively from the Calendar_Selector_Dialog result.
2. THE AppController SHALL NOT assign `GREGORIAN_DEFAULT` directly to a new project during `on_new_project()`.
3. WHERE the `GREGORIAN_DEFAULT` Python constant is still referenced elsewhere in the codebase (e.g., as a fallback in `Serializer.load()`), THE Serializer SHALL continue to function correctly using the constant until those references are separately addressed.
