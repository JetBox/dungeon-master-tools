# Requirements Document

## Introduction

This feature adds the ability to attach named entries to specific calendar days in the TTRPG DM tool. When a day is selected in the calendar view, an "Add Entry" button appears at the bottom of the view. Clicking it opens a form where the DM can enter a name for the entry. All entries for that day are then displayed whenever that day is selected. Entries are persisted as part of the project data.

## Glossary

- **Calendar_Tab**: The top-level widget that owns the calendar view and day detail sidebar.
- **CalendarDay**: A data model representing a single calendar date and its associated entries.
- **CalendarEntry**: A named item attached to a specific `CalendarDay`.
- **Day_Detail_Sidebar**: The panel shown below the calendar grid when a day is selected.
- **Add_Entry_Dialog**: The modal form that collects a name for a new `CalendarEntry`.
- **Project**: The top-level data model that owns all campaign data, including calendar entries.

## Requirements

### Requirement 1: Display "Add Entry" button when a day is selected

**User Story:** As a DM, I want an "Add Entry" button to appear when I select a calendar day, so that I can quickly add entries to that day.

#### Acceptance Criteria

1. WHEN a calendar day is selected, THE Day_Detail_Sidebar SHALL display an "Add Entry" button.
2. WHEN no calendar day is selected, THE Day_Detail_Sidebar SHALL hide the "Add Entry" button.

---

### Requirement 2: Add a named entry to a calendar day

**User Story:** As a DM, I want to enter a name for a new entry via a dialog, so that I can record events or notes for a specific day.

#### Acceptance Criteria

1. WHEN the "Add Entry" button is clicked, THE Add_Entry_Dialog SHALL open as a modal dialog.
2. THE Add_Entry_Dialog SHALL contain a text input field for the entry name and "OK" and "Cancel" buttons.
3. WHEN the "OK" button is clicked and the entry name field is non-empty, THE Add_Entry_Dialog SHALL accept and close.
4. IF the entry name field is empty when "OK" is clicked, THEN THE Add_Entry_Dialog SHALL remain open without creating an entry.
5. WHEN the "Cancel" button is clicked, THE Add_Entry_Dialog SHALL close without creating an entry.

---

### Requirement 3: Display entries for the selected day

**User Story:** As a DM, I want to see all entries for a selected day in the sidebar, so that I can review what is scheduled or noted for that day.

#### Acceptance Criteria

1. WHEN a calendar day with one or more entries is selected, THE Day_Detail_Sidebar SHALL display the name of each entry associated with that day.
2. WHEN a calendar day with no entries is selected, THE Day_Detail_Sidebar SHALL display no entry items.
3. WHEN a new entry is successfully added, THE Day_Detail_Sidebar SHALL immediately display the new entry without requiring the day to be re-selected.

---

### Requirement 4: Persist calendar entries as part of the project

**User Story:** As a DM, I want calendar entries to be saved and loaded with the project file, so that my notes are not lost between sessions.

#### Acceptance Criteria

1. THE Project SHALL store all `CalendarEntry` objects associated with each `CalendarDay`.
2. WHEN a project is saved, THE Serializer SHALL write all calendar entries to the project JSON file.
3. WHEN a project is loaded, THE Serializer SHALL restore all calendar entries from the project JSON file.
4. IF a loaded project JSON file contains no calendar entry data, THEN THE Serializer SHALL initialise the calendar entries collection as empty.
