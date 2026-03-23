# Tasks

## Task List

- [x] 1. Add `RoundTrackerItem` dataclass to `src/models.py`
  - [x] 1.1 Add `RoundTrackerItem(name: str, rounds: int)` dataclass below the existing `Project` dataclass

- [x] 2. Create `ItemWidget` in `src/views/item_widget.py`
  - [x] 2.1 Create `src/views/item_widget.py` with `ItemWidget(QFrame)` class
  - [x] 2.2 Use `QHBoxLayout` with left-aligned name label and right-aligned rounds label
  - [x] 2.3 Set `QFrame.Shape.Box` for rectangular border appearance

- [x] 3. Create `AddItemDialog` in `src/views/add_item_dialog.py`
  - [x] 3.1 Create `src/views/add_item_dialog.py` with `AddItemDialog(QDialog)` class mirroring `ProjectDialog` structure
  - [x] 3.2 Add `QLineEdit` for Name and `QSpinBox` (minimum=1) for Rounds
  - [x] 3.3 Add "Add" and "Cancel" buttons
  - [x] 3.4 Add hidden red `QLabel` for inline error messages
  - [x] 3.5 Implement `_on_add` validation: reject blank/whitespace name, show error and keep dialog open
  - [x] 3.6 Implement `get_item()` returning a `RoundTrackerItem` from the validated inputs

- [x] 4. Create `RoundTrackerTab` in `src/views/round_tracker_tab.py`
  - [x] 4.1 Create `src/views/round_tracker_tab.py` with `RoundTrackerTab(QWidget)` class
  - [x] 4.2 Add "Add Item" `QPushButton` at the top
  - [x] 4.3 Add `QScrollArea` containing an inner `QWidget` with `QVBoxLayout` and a bottom spacer
  - [x] 4.4 Implement `_on_add_item`: open `AddItemDialog`, on accept append a new `ItemWidget` to the scroll area layout

- [x] 5. Register `RoundTrackerTab` in `MainWindow`
  - [x] 5.1 Import `RoundTrackerTab` in `src/views/main_window.py`
  - [x] 5.2 Instantiate `RoundTrackerTab` and add it as the "Round Tracker" tab in the `QTabWidget`

- [x] 6. Refactor `ItemWidget` to support inline editing and action buttons
  - [x] 6.1 Replace name `QLabel` with `QLineEdit(item.name)` and store `_last_valid_name = item.name`
    - Connect `editingFinished` to a slot that reverts to `_last_valid_name` if text is blank/whitespace
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 6.2 Replace rounds `QLabel` with `QSpinBox(minimum=0, value=item.rounds)`
    - _Requirements: 8.1, 8.2, 8.3_
  - [x] 6.3 Add circular `-` `QPushButton` left of the `QSpinBox`
    - Fixed size 28×28 px, `border-radius: 14px` via stylesheet
    - Connect to slot that calls `self._spin.setValue(max(0, self._spin.value() - 1))`
    - _Requirements: 9.1, 9.2, 9.3_
  - [x] 6.4 Add circular `+` `QPushButton` right of the `QSpinBox`
    - Fixed size 28×28 px, `border-radius: 14px` via stylesheet
    - Connect to slot that calls `self._spin.setValue(self._spin.value() + 1)`
    - _Requirements: 10.1, 10.2_
  - [x] 6.5 Add `X` `QPushButton` in a top-right-aligned row above the main row
    - Connect to a slot that calls `self.setParent(None)` to remove the widget from the layout
    - _Requirements: 11.1, 11.2_
  - [x] 6.6 Add `get_rounds() -> int` method returning `self._spin.value()`
    - _Requirements: 12.2_

- [x] 7. Add `Sort` button to `RoundTrackerTab`
  - [x] 7.1 Add `QPushButton("Sort")` below the "Add Item" button in `RoundTrackerTab.__init__`
    - Connect to `self._on_sort`
    - _Requirements: 12.1_
  - [x] 7.2 Implement `_on_sort` in `RoundTrackerTab`
    - Collect all `ItemWidget` instances from `_inner_layout` (skip the `QSpacerItem`)
    - Remove each widget from the layout without deleting it
    - Re-insert in stable-sorted order using `sorted(..., key=lambda w: w.get_rounds())`
    - Re-add the spacer last
    - _Requirements: 12.2, 12.3_

- [x] 8. Checkpoint — verify all new interactions work end-to-end
  - Ensure all tests pass, ask the user if questions arise.
