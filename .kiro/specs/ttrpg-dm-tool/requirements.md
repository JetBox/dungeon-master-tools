# Requirements Document

## Introduction

A desktop campaign management tool for Dungeon Masters running sword-and-sorcery fantasy TTRPGs virtually. The application is system-agnostic and built with Python and PyQt6. It organizes campaign data into "projects" (one per campaign), stored as JSON files. The initial scope covers the core application shell: a scalable main window with a tabbed interface and a File menu that supports creating, saving, and loading projects.

## Glossary

- **Application**: The PyQt6 desktop program described in this document.
- **Project**: A named collection of campaign data for a single TTRPG campaign, persisted as a JSON file on disk.
- **Main_Window**: The top-level application window containing the menu bar and tab area.
- **Tab_Area**: The tabbed widget inside the Main_Window that hosts discrete functional views.
- **File_Menu**: The "File" entry in the application menu bar, providing project management actions.
- **Project_Dialog**: A modal dialog that prompts the user to enter a name when creating a new project.
- **Serializer**: The component responsible for reading and writing Project data to and from JSON files.

---

## Requirements

### Requirement 1: Application Launch

**User Story:** As a Dungeon Master, I want the application to open a usable main window, so that I can begin managing my campaign.

#### Acceptance Criteria

1. THE Main_Window SHALL display a title bar, a menu bar, and a Tab_Area on launch.
2. THE Main_Window SHALL open in a default size that makes all UI elements visible without scrolling.

---

### Requirement 2: Scalable Window Layout

**User Story:** As a Dungeon Master, I want to resize the application window freely, so that no UI elements disappear or become inaccessible at any window size.

#### Acceptance Criteria

1. WHILE the Main_Window is being resized, THE Tab_Area SHALL remain fully visible within the window bounds.
2. WHILE the Main_Window is being resized, THE Application SHALL reflow all child widgets to fit the new dimensions without clipping or hiding any element.
3. THE Main_Window SHALL enforce a minimum size below which the window cannot be reduced.

---

### Requirement 3: Tabbed Interface

**User Story:** As a Dungeon Master, I want a tabbed interface in the main window, so that I can navigate between different campaign management views.

#### Acceptance Criteria

1. THE Tab_Area SHALL display at least one tab on application launch.
2. WHEN a tab is selected, THE Tab_Area SHALL bring the corresponding view to the foreground.
3. THE Main_Window SHALL display a placeholder "Campaign Overview" tab on initial launch when no project is loaded.

---

### Requirement 4: Create New Project

**User Story:** As a Dungeon Master, I want to create a new project and give it a name, so that I can start organizing a new campaign.

#### Acceptance Criteria

1. WHEN the user selects "New Project" from the File_Menu, THE Application SHALL open the Project_Dialog.
2. WHEN the user confirms the Project_Dialog with a non-empty name, THE Application SHALL create a new Project with that name and set it as the active project.
3. IF the user confirms the Project_Dialog with an empty name, THEN THE Project_Dialog SHALL display an inline validation message and remain open.
4. IF the user cancels the Project_Dialog, THEN THE Application SHALL discard the dialog and leave the current application state unchanged.
5. WHEN a new Project is created, THE Main_Window SHALL update the title bar to reflect the new project name.

---

### Requirement 5: Save Project

**User Story:** As a Dungeon Master, I want to save my current project to disk, so that my campaign data is not lost between sessions.

#### Acceptance Criteria

1. WHEN the user selects "Save Project" from the File_Menu and an active project exists, THE Serializer SHALL write the Project data to a JSON file at a user-chosen file path.
2. WHEN the user selects "Save Project" and no active project exists, THE Application SHALL display an informational message stating that there is no project to save.
3. THE Serializer SHALL produce a JSON file that is valid and human-readable (pretty-printed with 2-space or 4-space indentation).
4. IF a file write error occurs, THEN THE Application SHALL display an error message describing the failure and leave the existing file unchanged.

---

### Requirement 6: Load Existing Project

**User Story:** As a Dungeon Master, I want to load a previously saved project, so that I can continue working on an existing campaign.

#### Acceptance Criteria

1. WHEN the user selects "Load Project" from the File_Menu, THE Application SHALL open a file picker filtered to JSON files.
2. WHEN the user selects a valid JSON project file, THE Serializer SHALL parse the file and set the loaded Project as the active project.
3. WHEN a project is loaded, THE Main_Window SHALL update the title bar to reflect the loaded project name.
4. IF the selected file is not a valid project JSON, THEN THE Application SHALL display an error message and leave the current application state unchanged.
5. IF a file read error occurs, THEN THE Application SHALL display an error message describing the failure.

---

### Requirement 7: Project Data Serialization

**User Story:** As a Dungeon Master, I want my project data stored as a JSON file, so that it is portable and inspectable outside the application.

#### Acceptance Criteria

1. THE Serializer SHALL serialize a Project to a JSON object containing at minimum a `name` field and a `version` field.
2. THE Serializer SHALL deserialize a JSON object into a Project, restoring all fields present in the file.
3. FOR ALL valid Project objects, serializing then deserializing SHALL produce a Project equivalent to the original (round-trip property).
4. IF a required field is missing from the JSON during deserialization, THEN THE Serializer SHALL raise a descriptive error identifying the missing field.
