# Tasks

## Task List

- [ ] 1. Extend data models in `src/models.py`
  - [ ] 1.1 Add `CalendarEntry(name: str)` dataclass
  - [ ] 1.2 Add `entries: list[CalendarEntry]` field (default empty list) to the existing `CalendarDay` dataclass
  - [ ] 1.3 Add `calendar_days: list[CalendarDay]` field (default empty list) to the `Project` dataclass

- [ ] 2. Create `AddEntryDialog` in `src/views/add_entry_dialog.py`
  - [ ] 2.1 Create `AddEntryDialog(QDialog)` with a `QLineEdit` for entry name, hidden red `QLabel` for inline errors, and "OK" / "Cancel" buttons
  - [ ] 2.2 Implement `_on_ok`: strip whitespace from name; if empty show error and keep dialog open, otherwise accept
  - [ ] 2.3 Implement `get_entry() -> CalendarEntry` returning a `CalendarEntry` from the validated input

- [ ] 3. Extend `DayDetailSidebar` in `src/views/calendar_tab.py`
  - [ ] 3.1 Add `add_entry_requested = pyqtSignal()` signal
  - [ ] 3.2 Add `QPushButton("Add Entry")` below the date label; connect to `add_entry_requested`; show/hide with the sidebar
  - [ ] 3.3 Add an entries `QVBoxLayout` container below the button to hold one `QLabel` per entry
  - [ ] 3.4 Implement `set_entries(entries: list[CalendarEntry])`: clear the container and repopulate with a `QLabel` per entry name
  - [ ] 3.5 Implement `add_entry(entry: CalendarEntry)`: append a single `QLabel` for the entry name to the container

- [ ] 4. Extend `CalendarTab` in `src/views/calendar_tab.py`
  - [ ] 4.1 Add `self._entries: dict[datetime.date, list[CalendarEntry]] = {}` to `__init__`
  - [ ] 4.2 Connect `self._sidebar.add_entry_requested` to `self._on_add_entry_requested`
  - [ ] 4.3 Update `_on_day_clicked` to call `self._sidebar.set_entries(self._entries.get(date, []))` when showing a day
  - [ ] 4.4 Implement `_on_add_entry_requested`: open `AddEntryDialog`; on accept, append the new `CalendarEntry` to `self._entries[self._selected_date]` and call `self._sidebar.add_entry(entry)`
  - [ ] 4.5 Implement `load_from_project(project: Project)`: populate `self._entries` from `project.calendar_days`; refresh sidebar if a day is currently selected
  - [ ] 4.6 Implement `flush_to_project(project: Project)`: write `self._entries` back into `project.calendar_days`

- [ ] 5. Update `Serializer` in `src/serializer.py`
  - [ ] 5.1 Add `_to_serializable(data)` helper that recursively converts `datetime.date` dicts `{"year", "month", "day"}` to ISO strings
  - [ ] 5.2 In `save`, apply `_to_serializable` to the `asdict(project)` output before writing JSON
  - [ ] 5.3 In `load`, reconstruct `CalendarDay` and `CalendarEntry` objects from `data.get("calendar_days", [])`; parse date strings with `datetime.date.fromisoformat`; wrap `ValueError`/`KeyError` in `ProjectLoadError`

- [ ] 6. Expose `calendar_tab` in `MainWindow` and update `AppController`
  - [ ] 6.1 Add a `calendar_tab` property to `MainWindow` returning the `CalendarTab` instance
  - [ ] 6.2 In `AppController.on_load_project`, call `self._window.calendar_tab.load_from_project(project)` after loading
  - [ ] 6.3 In `AppController.on_save_project`, call `self._window.calendar_tab.flush_to_project(self._project)` before saving

- [ ] 7. Checkpoint — verify all new interactions work end-to-end
  - Ensure add entry dialog opens, entries appear in sidebar, and entries survive a save/load cycle.
