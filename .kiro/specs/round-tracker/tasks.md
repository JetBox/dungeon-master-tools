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
