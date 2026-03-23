# Design Document: Round Tracker

## Overview

The Round Tracker is a new tab added to the existing TTRPG DM Tool PyQt6 desktop application. It lets a DM track named, round-counted events (torch durations, spell timers, encounter countdowns) during a dungeon crawl session.

The feature adds:
- A `RoundTrackerItem` dataclass to `src/models.py`
- A `RoundTrackerTab` widget in `src/views/round_tracker_tab.py`
- An `AddItemDialog` widget in `src/views/add_item_dialog.py`
- An `ItemWidget` widget in `src/views/item_widget.py`
- A new tab registered in `MainWindow`

No new controller logic is required — the Round Tracker tab is self-contained and manages its own in-memory state.

---

## Architecture

The feature follows the same MVC-lite pattern already in use:

```
MainWindow
  └── QTabWidget
        ├── QWidget (Campaign Overview — existing)
        └── RoundTrackerTab (new)
              ├── QPushButton "Add Item"
              ├── QScrollArea
              │     └── QVBoxLayout
              │           ├── ItemWidget
              │           ├── ItemWidget
              │           └── ...
              └── AddItemDialog (opened on demand)
```

State lives entirely in `RoundTrackerTab` as a list of `RoundTrackerItem` objects. No persistence to disk is required for this scope.

---

## Components and Interfaces

### `RoundTrackerItem` (src/models.py)

```python
@dataclass
class RoundTrackerItem:
    name: str
    rounds: int
```

### `RoundTrackerTab` (src/views/round_tracker_tab.py)

```python
class RoundTrackerTab(QWidget):
    def __init__(self, parent=None) -> None: ...
    def _on_add_item(self) -> None:
        """Open AddItemDialog; on accept, append ItemWidget to scroll area."""
```

Layout:
- `QVBoxLayout` at the top level
- `QPushButton("Add Item")` at the top
- `QScrollArea` below, containing a `QWidget` with a `QVBoxLayout` that holds `ItemWidget` instances
- A `QSpacerItem` at the bottom of the inner layout keeps widgets top-aligned

### `AddItemDialog` (src/views/add_item_dialog.py)

Mirrors `ProjectDialog` in structure.

```python
class AddItemDialog(QDialog):
    def __init__(self, parent=None) -> None: ...
    def _on_add(self) -> None:
        """Validate fields; show inline error or accept."""
    def get_item(self) -> RoundTrackerItem:
        """Return the validated RoundTrackerItem. Call only after Accepted."""
```

Fields:
- `QLineEdit` for Name
- `QSpinBox` (minimum=1, no upper bound set beyond Qt default) for Rounds
- `QLabel` for inline error messages (hidden by default, shown red on error)
- `QPushButton("Add")` and `QPushButton("Cancel")`

### `ItemWidget` (src/views/item_widget.py)

```python
class ItemWidget(QFrame):
    def __init__(self, item: RoundTrackerItem, parent=None) -> None: ...
```

Layout:
- `QHBoxLayout`
- `QLabel(item.name)` — left-aligned
- `QLabel(str(item.rounds))` — right-aligned (via `Qt.AlignmentFlag.AlignRight`)
- `QFrame.Shape.Box` gives the rectangular border

### `MainWindow` update (src/views/main_window.py)

Import and instantiate `RoundTrackerTab`, then add it as the second tab:

```python
self._round_tracker_tab = RoundTrackerTab()
self._tab_widget.addTab(self._round_tracker_tab, "Round Tracker")
```

---

## Data Models

```python
# src/models.py (addition)
@dataclass
class RoundTrackerItem:
    name: str       # non-empty string
    rounds: int     # integer > 0
```

Validation is enforced in `AddItemDialog`, not in the dataclass itself, consistent with how `Project` works (name validation lives in `ProjectDialog`).

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Invalid rounds input is rejected

*For any* value entered in the Rounds field that is not a whole integer greater than zero (including blank, zero, negative numbers, or non-numeric text), clicking "Add" should display an error message and leave the dialog open.

**Validates: Requirements 3.3, 4.2, 4.3**

### Property 2: Blank name is rejected

*For any* string composed entirely of whitespace (or the empty string) entered in the Name field, clicking "Add" should display an error message and leave the dialog open.

**Validates: Requirements 4.1**

### Property 3: Valid submission adds item to list

*For any* valid name (non-blank) and valid rounds value (integer > 0), clicking "Add" should close the dialog and result in a new `ItemWidget` appearing in the Round Tracker's item list, increasing the widget count by one.

**Validates: Requirements 5.1**

### Property 4: Item widget displays correct data

*For any* `RoundTrackerItem`, the `ItemWidget` constructed from it should display the item's name and round count as visible text within the widget.

**Validates: Requirements 5.3, 5.4**

### Property 5: State preserved across tab switches

*For any* set of items added to the Round Tracker, switching away from the tab and returning should result in the same number of `ItemWidget`s being present, each with the same name and round count as before the switch.

**Validates: Requirements 6.1, 6.2**

---

## Error Handling

| Scenario | Handling |
|---|---|
| Name field blank or whitespace-only | Inline red error label in `AddItemDialog`; dialog stays open |
| Rounds field blank | `QSpinBox` defaults to its minimum (1), so blank is not possible at submission; validation still guards against minimum value edge cases |
| Rounds value ≤ 0 | `QSpinBox` minimum is set to 1, preventing this at the widget level; `_on_add` validates as a second guard |
| User cancels dialog | Dialog closes, no item created, tracker state unchanged |

No disk I/O or network calls are involved, so no I/O error handling is needed for this feature.

---

## Testing Strategy

Per the project testing policy, unit tests are not required. The correctness properties above serve as the specification for any future automated testing.

If tests are added, the recommended approach is:

- Use `pytest-qt` for PyQt6 widget testing
- Use `hypothesis` for property-based testing
- Each property test should run a minimum of 100 iterations
- Tag each test referencing the design property, e.g.:
  `# Feature: round-tracker, Property 1: invalid rounds input is rejected`

**Unit test targets** (specific examples worth covering if tests are written):
- `MainWindow` tab widget contains a "Round Tracker" tab (Req 1.1)
- `AddItemDialog` contains Name input, Rounds spinbox, Add and Cancel buttons (Req 3.1, 3.2)
- `RoundTrackerTab` contains an "Add Item" button and a scroll area (Req 2.1, 5.2)
- Clicking Cancel closes dialog without adding items (Req 4.4)

**Property test targets**:
- Property 1: Generate invalid rounds values (0, negatives, non-numeric strings) → dialog rejects all
- Property 2: Generate whitespace/empty name strings → dialog rejects all
- Property 3: Generate valid (name, rounds) pairs → item count increases by 1 each time
- Property 4: Generate random `RoundTrackerItem` instances → widget text contains name and rounds
- Property 5: Generate random item sequences, simulate tab switch → all items preserved with correct data
