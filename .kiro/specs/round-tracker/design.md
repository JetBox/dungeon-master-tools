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
              ├── QPushButton "Sort"
              ├── QScrollArea
              │     └── QVBoxLayout
              │           ├── ItemWidget
              │           │     ├── QPushButton "X"  (top-right)
              │           │     ├── QLineEdit (name)
              │           │     ├── QPushButton "-"  (circular)
              │           │     ├── QSpinBox (rounds)
              │           │     └── QPushButton "+"  (circular)
              │           ├── ItemWidget
              │           └── ...
              └── AddItemDialog (opened on demand)
```

State lives entirely in `RoundTrackerTab` as a list of `ItemWidget` instances. No persistence to disk is required for this scope.

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
    def _on_sort(self) -> None:
        """Stable-sort all ItemWidgets by round count, lowest to highest."""
```

Layout:
- `QVBoxLayout` at the top level
- `QPushButton("Add Item")` and `QPushButton("Sort")` at the top
- `QScrollArea` below, containing a `QWidget` with a `QVBoxLayout` that holds `ItemWidget` instances
- A `QSpacerItem` at the bottom of the inner layout keeps widgets top-aligned

`_on_sort` implementation note: collect all `ItemWidget` instances from the inner layout (excluding the spacer), remove them, then re-insert in stable-sorted order using Python's `sorted()` (which is stable by default) keyed on each widget's current round count.

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
    def get_rounds(self) -> int:
        """Return the current round count value."""
```

Layout:
- Outer `QVBoxLayout` containing:
  - Top row: `QPushButton("X")` right-aligned (delete button)
  - Main row: `QHBoxLayout` with:
    - `QLineEdit(item.name)` — left-aligned, editable
    - `QPushButton("-")` — circular, fixed size
    - `QSpinBox(minimum=0, value=item.rounds)` — editable numeric field
    - `QPushButton("+")` — circular, fixed size
- `QFrame.Shape.Box` gives the rectangular border

Behaviour details:
- **Name editing**: `QLineEdit` is editable. On `editingFinished`, if the text is blank/whitespace, revert to the previous non-blank value stored in `_last_valid_name`.
- **Round count editing**: `QSpinBox` with `minimum=0`. Non-numeric input is prevented by `QSpinBox` natively; values below 0 are clamped by the minimum setting.
- **'-' button**: decrements `QSpinBox` value by 1; `QSpinBox.minimum=0` prevents going below zero.
- **'+' button**: increments `QSpinBox` value by 1.
- **'X' button**: emits a signal or calls a callback so `RoundTrackerTab` can remove this widget from the layout. The widget calls `self.setParent(None)` after removal.

Circular button styling: set a fixed width/height (e.g. 28×28 px) and apply a border-radius of half that value via stylesheet to achieve a circular appearance.

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
    rounds: int     # integer >= 0
```

Validation is enforced in `AddItemDialog` (initial creation) and `ItemWidget` (inline editing), not in the dataclass itself, consistent with how `Project` works.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Invalid rounds input is rejected

*For any* value entered in the Rounds field of `AddItemDialog` that is not a whole integer greater than zero (including blank, zero, negative numbers, or non-numeric text), clicking "Add" should display an error message and leave the dialog open.

**Validates: Requirements 3.3, 4.2, 4.3**

### Property 2: Blank name is rejected in dialog

*For any* string composed entirely of whitespace (or the empty string) entered in the Name field of `AddItemDialog`, clicking "Add" should display an error message and leave the dialog open.

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

### Property 6: Name edit round-trip

*For any* non-blank string entered into an `ItemWidget`'s name field, after the field loses focus the displayed name should equal the entered string. As an edge case: if the entered string is blank or whitespace-only, the displayed name should revert to the previous non-blank value.

**Validates: Requirements 7.2, 7.3**

### Property 7: Round count edit round-trip

*For any* non-negative integer entered into an `ItemWidget`'s round count field, the displayed value should equal that integer. As edge cases: any value below zero should be clamped to zero; any non-numeric input should revert to the previous valid value.

**Validates: Requirements 8.2, 8.3, 8.4**

### Property 8: Increment and decrement change count by one

*For any* `ItemWidget` with a current round count `n`, clicking '+' should result in a round count of `n + 1`, and clicking '-' should result in a round count of `max(0, n - 1)`. In particular, clicking '-' when `n = 0` should leave the count at 0.

**Validates: Requirements 9.2, 9.3, 10.2**

### Property 9: Delete removes exactly one widget

*For any* list of `ItemWidget`s in the Round Tracker, clicking the 'X' button on any one widget should reduce the total widget count by exactly one, and that specific widget should no longer be present in the list.

**Validates: Requirements 11.2**

### Property 10: Sort produces non-decreasing order

*For any* list of `ItemWidget`s with arbitrary round counts, clicking "Sort" should reorder them such that the sequence of round counts is non-decreasing (lowest to highest).

**Validates: Requirements 12.2**

### Property 11: Sort is stable

*For any* list of `ItemWidget`s where two or more widgets share the same round count, clicking "Sort" should preserve their relative order among those equal-count widgets.

**Validates: Requirements 12.3**

---

## Error Handling

| Scenario | Handling |
|---|---|
| Name field blank or whitespace-only (dialog) | Inline red error label in `AddItemDialog`; dialog stays open |
| Rounds field blank (dialog) | `QSpinBox` defaults to its minimum (1), so blank is not possible at submission; validation still guards against minimum value edge cases |
| Rounds value ≤ 0 (dialog) | `QSpinBox` minimum is set to 1, preventing this at the widget level; `_on_add` validates as a second guard |
| User cancels dialog | Dialog closes, no item created, tracker state unchanged |
| Name field cleared in `ItemWidget` | `editingFinished` handler reverts to `_last_valid_name` |
| Round count below zero in `ItemWidget` | `QSpinBox` minimum=0 clamps the value automatically |
| Non-numeric input in round count field | `QSpinBox` rejects non-numeric input natively |
| 'X' clicked on widget | Widget is removed from layout and destroyed; remaining widgets are unaffected |
| Sort with zero or one item | No-op; list remains unchanged |

No disk I/O or network calls are involved, so no I/O error handling is needed for this feature.

---

## Testing Strategy

Per the project testing policy, unit tests are not required. The correctness properties above serve as the specification for any future automated testing.

If tests are added, the recommended approach is:

- Use `pytest-qt` for PyQt6 widget testing
- Use `hypothesis` for property-based testing
- Each property test should run a minimum of 100 iterations
- Tag each test referencing the design property, e.g.:
  `# Feature: round-tracker, Property 6: name edit round-trip`

**Property test targets**:
- Property 1: Generate invalid rounds values (0, negatives, non-numeric strings) → dialog rejects all
- Property 2: Generate whitespace/empty name strings → dialog rejects all
- Property 3: Generate valid (name, rounds) pairs → item count increases by 1 each time
- Property 4: Generate random `RoundTrackerItem` instances → widget text contains name and rounds
- Property 5: Generate random item sequences, simulate tab switch → all items preserved with correct data
- Property 6: Generate random non-blank name strings → widget displays entered name; generate blank/whitespace strings → widget reverts to previous name
- Property 7: Generate random non-negative integers → widget displays entered value; generate negatives → clamped to 0; generate non-numeric strings → reverts to previous value
- Property 8: Generate random round counts → '+' increases by 1; '-' decreases by 1 with floor at 0
- Property 9: Generate random lists of items, pick a random widget to delete → count decreases by 1, deleted widget absent
- Property 10: Generate random lists of items with arbitrary round counts → after sort, sequence is non-decreasing
- Property 11: Generate random lists with duplicate round counts → after sort, relative order of equal-count items is preserved
