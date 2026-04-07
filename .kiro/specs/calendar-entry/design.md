# Design Document: Calendar Entry

## Overview

This feature adds the ability to attach named entries to specific calendar days in the TTRPG DM Tool. It extends the existing `CalendarTab` and `DayDetailSidebar` with an "Add Entry" button and an entry list, adds `CalendarEntry` and `CalendarDay` data models, and wires persistence through the existing `Serializer`.

The feature adds:
- `CalendarEntry` and `CalendarDay` dataclasses to `src/models.py`
- `AddEntryDialog` in `src/views/add_entry_dialog.py`
- Updates to `DayDetailSidebar` in `src/views/calendar_tab.py` to show entries and the "Add Entry" button
- Updates to `CalendarTab` to manage entry state and connect the dialog
- Updates to `Project` in `src/models.py` to store calendar entries
- Updates to `Serializer` in `src/serializer.py` to persist and restore calendar entries

---

## Architecture

The feature follows the same MVC-lite pattern already in use:

```
CalendarTab
  ├── CalendarView  (unchanged)
  └── DayDetailSidebar  (extended)
        ├── QLabel (date)
        ├── QPushButton "Add Entry"  (new)
        ├── QVBoxLayout (entry list)  (new)
        │     ├── QLabel (entry name)
        │     └── ...
        └── QPushButton "✕" (close)

AddEntryDialog  (new, opened on demand)
  ├── QLineEdit (entry name)
  ├── QLabel (inline error, hidden by default)
  ├── QPushButton "OK"
  └── QPushButton "Cancel"
```

Entry state is owned by `CalendarTab` as a `dict[datetime.date, list[CalendarEntry]]`. When a project is loaded, `CalendarTab` is refreshed from the `Project` model. When a project is saved, `CalendarTab` writes its state back to `Project` before serialization.

---

## Components and Interfaces

### `CalendarEntry` (src/models.py)

```python
@dataclass
class CalendarEntry:
    name: str  # non-empty string
```

### `CalendarDay` (src/models.py)

```python
@dataclass
class CalendarDay:
    date: datetime.date
    entries: list[CalendarEntry] = field(default_factory=list)
```

The existing `CalendarDay` dataclass already exists with only a `date` field; it will be extended with `entries`.

### `Project` (src/models.py)

```python
@dataclass
class Project:
    name: str
    version: str = "1.0"
    calendar_days: list[CalendarDay] = field(default_factory=list)
```

`calendar_days` is a flat list of `CalendarDay` objects that have at least one entry. Days with no entries are not stored.

### `AddEntryDialog` (src/views/add_entry_dialog.py)

```python
class AddEntryDialog(QDialog):
    def __init__(self, parent=None) -> None: ...
    def _on_ok(self) -> None:
        """Validate name field; show inline error or accept."""
    def get_entry(self) -> CalendarEntry:
        """Return the validated CalendarEntry. Call only after Accepted."""
```

Fields:
- `QLineEdit` for entry name
- `QLabel` for inline error (hidden by default, shown red on validation failure)
- `QPushButton("OK")` and `QPushButton("Cancel")`

Validation: name must be non-empty after stripping whitespace. If blank, show error and keep dialog open.

### `DayDetailSidebar` (src/views/calendar_tab.py — extended)

New public methods:

```python
def set_entries(self, entries: list[CalendarEntry]) -> None:
    """Replace the displayed entry list with the given entries."""

def add_entry(self, entry: CalendarEntry) -> None:
    """Append a single entry label to the displayed list."""
```

New signal:

```python
add_entry_requested = pyqtSignal()
```

Layout changes:
- Add `QPushButton("Add Entry")` below the date label; connect to `add_entry_requested`
- Add a `QVBoxLayout` (entries container) below the button to hold `QLabel` widgets, one per entry
- The "Add Entry" button is shown only when the sidebar is visible (i.e. a day is selected)

### `CalendarTab` (src/views/calendar_tab.py — extended)

New state:

```python
self._entries: dict[datetime.date, list[CalendarEntry]] = {}
```

New/updated methods:

```python
def _on_add_entry_requested(self) -> None:
    """Open AddEntryDialog; on accept, store and display the new entry."""

def load_from_project(self, project: Project) -> None:
    """Populate _entries from the project's calendar_days list."""

def flush_to_project(self, project: Project) -> None:
    """Write _entries back into project.calendar_days before saving."""
```

`_on_day_clicked` is updated to call `self._sidebar.set_entries(...)` with the entries for the clicked date.

### `AppController` (src/controller.py — extended)

- After loading a project, call `self._window.calendar_tab.load_from_project(project)`
- Before saving a project, call `self._window.calendar_tab.flush_to_project(self._project)`

### `MainWindow` (src/views/main_window.py — minor)

Expose `calendar_tab` as a property so `AppController` can call `load_from_project` / `flush_to_project`.

### `Serializer` (src/serializer.py — extended)

Serialization uses `dataclasses.asdict` which already handles nested dataclasses. The `load` method must reconstruct `CalendarDay` and `CalendarEntry` objects from the raw dict.

```python
# In Serializer.load:
calendar_days = []
for day_data in data.get("calendar_days", []):
    entries = [CalendarEntry(name=e["name"]) for e in day_data.get("entries", [])]
    date = datetime.date.fromisoformat(day_data["date"])
    calendar_days.append(CalendarDay(date=date, entries=entries))
```

`datetime.date` is not JSON-serializable by default. `asdict` will produce a dict `{"year": ..., "month": ..., "day": ...}` for `datetime.date`. The serializer must handle this by converting dates to ISO strings before writing and parsing them back on load.

A custom `_serialize_project` helper will convert the project dict, replacing any `datetime.date` dicts with ISO strings:

```python
def _to_serializable(data):
    """Recursively convert datetime.date dicts to ISO strings."""
    if isinstance(data, dict):
        if set(data.keys()) == {"year", "month", "day"}:
            return datetime.date(data["year"], data["month"], data["day"]).isoformat()
        return {k: _to_serializable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_serializable(i) for i in data]
    return data
```

---

## Data Models

```python
# src/models.py additions / changes

@dataclass
class CalendarEntry:
    name: str  # non-empty; validated at dialog level

@dataclass
class CalendarDay:
    date: datetime.date
    entries: list[CalendarEntry] = field(default_factory=list)

@dataclass
class Project:
    name: str
    version: str = "1.0"
    calendar_days: list[CalendarDay] = field(default_factory=list)
```

JSON representation of a saved project with calendar entries:

```json
{
    "name": "My Campaign",
    "version": "1.0",
    "calendar_days": [
        {
            "date": "2025-06-09",
            "entries": [
                {"name": "Dragon attack"},
                {"name": "Market day"}
            ]
        }
    ]
}

```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Valid name accepted by dialog

*For any* non-empty, non-whitespace string entered as the entry name in `AddEntryDialog`, clicking "OK" should close the dialog with an Accepted result and `get_entry()` should return a `CalendarEntry` whose name equals the trimmed input.

**Validates: Requirements 2.3**

### Property 2: Blank or whitespace name rejected by dialog

*For any* string composed entirely of whitespace characters (including the empty string) entered as the entry name in `AddEntryDialog`, clicking "OK" should leave the dialog open without accepting, and no `CalendarEntry` should be created.

**Validates: Requirements 2.4**

### Property 3: Sidebar displays all entries for the selected day

*For any* non-empty list of `CalendarEntry` objects associated with a calendar day, selecting that day should cause the `DayDetailSidebar` to display a label containing each entry's name.

**Validates: Requirements 3.1**

### Property 4: Sidebar immediately shows new entry after add

*For any* valid entry name added via `AddEntryDialog` while a day is selected, the `DayDetailSidebar` should immediately display that entry name without requiring the day to be re-selected.

**Validates: Requirements 3.3**

### Property 5: Serialization round-trip preserves all calendar entries

*For any* `Project` containing `CalendarDay` objects with associated `CalendarEntry` objects, serializing the project to JSON and then deserializing it should produce a `Project` with identical calendar days and entries (same dates, same entry names, same counts).

**Validates: Requirements 4.1, 4.2, 4.3**

---

## Error Handling

| Scenario | Handling |
|---|---|
| Entry name blank or whitespace-only | Inline red error label in `AddEntryDialog`; dialog stays open; no entry created |
| User cancels `AddEntryDialog` | Dialog closes, no entry created, sidebar and state unchanged |
| Project JSON missing `calendar_days` key | `Serializer.load` defaults to empty list; no error raised |
| Project JSON has malformed date string | `datetime.date.fromisoformat` raises `ValueError`; wrap in `ProjectLoadError` |
| Project JSON has entry missing `name` key | `KeyError` raised during load; wrap in `ProjectLoadError` |
| `flush_to_project` called with no project | Guard in `AppController`; only called when `self._project is not None` |

---

## Testing Strategy

Per the project testing policy, unit tests are not required. The correctness properties above serve as the specification for any future automated testing.

If tests are added, the recommended approach is:

- Use `pytest-qt` for PyQt6 widget testing
- Use `hypothesis` for property-based testing
- Each property test should run a minimum of 100 iterations
- Tag each test referencing the design property, e.g.:
  `# Feature: calendar-entry, Property 5: serialization round-trip preserves all calendar entries`

**Property test targets**:
- Property 1: Generate random non-empty strings → dialog accepts, `get_entry().name` equals trimmed input
- Property 2: Generate whitespace/empty strings → dialog stays open, no entry created
- Property 3: Generate random lists of `CalendarEntry` objects → all names appear in sidebar after day selection
- Property 4: Generate random valid entry names → name appears in sidebar immediately after add, without re-selecting the day
- Property 5: Generate random `Project` instances with varying `CalendarDay`/`CalendarEntry` data → serialize then deserialize produces equivalent project
