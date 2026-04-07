# Tasks

## Task List

- [x] 1. Add new data models to `src/models.py`
  - [x] 1.1 Add `EraDirection` enum with `ASCENDING` and `DESCENDING` values
  - [x] 1.2 Add `MonthDefinition(name: str, day_count: int)` dataclass with `__post_init__` validation (5 ≤ day_count ≤ 100)
  - [x] 1.3 Add `LunarCycle(name: str, phase_interval: int, phase_offset: int = 0)` dataclass with `__post_init__` validation (phase_interval ≥ 1)
  - [x] 1.4 Add `IntercalaryPeriod(name: str, day_count: int, after_month: int)` dataclass with `__post_init__` validation (day_count ≥ 1)
  - [x] 1.5 Add `Era(name: str, starting_year: int, direction: EraDirection)` dataclass
  - [x] 1.6 Add `CalendarDefinition` dataclass with fields `name`, `months`, `week_length`, `weekday_names`, `hours_per_day`, `lunar_cycles`, `intercalary_periods`, `eras`; add `__post_init__` validation for all range and length constraints
  - [x] 1.7 Add `GREGORIAN_DEFAULT` module-level constant with 12 months, 7-day week, 24 hours, BC/AD eras

- [x] 2. Add `FantasyDateTime` to `src/models.py`
  - [x] 2.1 Add `PHASE_NAMES` constant list of 8 lunar phase name strings
  - [x] 2.2 Add `FantasyDateTime` dataclass with fields `calendar`, `year`, `month`, `day`, `hour`, `minute`, `second`, `era`; add `__post_init__` validation for month, day, and hour ranges
  - [x] 2.3 Implement `total_elapsed_days(self) -> int`: sum all days from year 1 day 1 through self, including intercalary days inserted after each month
  - [x] 2.4 Implement `day_of_week(self) -> int`: return `total_elapsed_days() % self.calendar.week_length`
  - [x] 2.5 Implement `add_seconds(self, delta: int) -> FantasyDateTime`: carry/borrow across seconds → minutes → hours → days → months (respecting each month's day_count and intercalary periods) → years; return new `FantasyDateTime`
  - [x] 2.6 Implement `lunar_phase(self, cycle: LunarCycle) -> str`: return `PHASE_NAMES[(total_elapsed_days() + cycle.phase_offset) // cycle.phase_interval % 8]`

- [x] 3. Update `Project` in `src/models.py`
  - [x] 3.1 Add `calendar_definition: CalendarDefinition` field (default `GREGORIAN_DEFAULT`) to `Project`
  - [x] 3.2 Add `tracked_date: FantasyDateTime | None` field (default `None`) to `Project`

- [x] 4. Update `CalendarView` in `src/views/calendar_tab.py`
  - [x] 4.1 Add `calendar_def: CalendarDefinition` parameter to `CalendarView.__init__`; store as `self._calendar_def`
  - [x] 4.2 Replace hardcoded `12`-month wrap logic in `_go_prev_month` / `_go_next_month` with `len(self._calendar_def.months)`
  - [x] 4.3 In `_rebuild_grid`, replace `calendar.Calendar` logic with a loop from day 1 to `self._calendar_def.months[self._month - 1].day_count`; compute starting column using `FantasyDateTime.day_of_week` for the first day of the month
  - [x] 4.4 In `_rebuild_grid`, replace hardcoded weekday headers with `self._calendar_def.weekday_names` (abbreviated to first 3 chars)
  - [x] 4.5 In `_rebuild_grid`, set month label to `self._calendar_def.months[self._month - 1].name + " " + str(self._year)`
  - [x] 4.6 Add `set_calendar(self, cal: CalendarDefinition) -> None`: update `self._calendar_def` and call `_rebuild_grid`
  - [x] 4.7 Update `refresh_states` to accept `FantasyDateTime` instead of `datetime.datetime`; compare using year/month/day fields

- [x] 5. Update `DayDetailSidebar` in `src/views/calendar_tab.py`
  - [x] 5.1 Add a `_lunar_container` `QVBoxLayout` section below the entries area
  - [x] 5.2 Add `show_lunar_phases(self, fdt: FantasyDateTime, cal: CalendarDefinition) -> None`: clear `_lunar_container`; for each `LunarCycle` in `cal.lunar_cycles`, add a `QLabel` showing `"{cycle.name}: {fdt.lunar_phase(cycle)}"`; hide the section if no lunar cycles

- [x] 6. Update `CalendarTab` in `src/views/calendar_tab.py`
  - [x] 6.1 Add `calendar_def: CalendarDefinition | None = None` parameter to `__init__`; default to `GREGORIAN_DEFAULT`; store as `self._calendar_def`
  - [x] 6.2 Replace `self._tracked_date` (was `datetime.datetime`) with a `FantasyDateTime` initialised from the real-world date using `GREGORIAN_DEFAULT` (or the provided `calendar_def`)
  - [x] 6.3 Update `_on_time_adjusted` to call `self._tracked_date = self._tracked_date.add_seconds(delta)` instead of `timedelta`
  - [x] 6.4 Update `_format_tracked_date` to build the banner string using `CalendarDefinition` month names, weekday names, and era name
  - [x] 6.5 Update `_on_day_clicked` to call `self._sidebar.show_lunar_phases(fdt, self._calendar_def)` when showing a day
  - [x] 6.6 Implement `load_from_project(self, project: Project) -> None`: set `self._calendar_def`, update `CalendarView` via `set_calendar`, set `self._tracked_date` from `project.tracked_date` (or initialise from today if `None`), refresh view
  - [x] 6.7 Implement `flush_to_project(self, project: Project) -> None`: write `self._tracked_date` and `self._calendar_def` back to `project`

- [x] 7. Update `Serializer` in `src/serializer.py`
  - [x] 7.1 Add `_to_serializable(data)` helper that recursively converts `Enum` instances to their `.value` strings (for `EraDirection`)
  - [x] 7.2 In `save`, apply `_to_serializable` to the `asdict(project)` output before writing JSON
  - [x] 7.3 Add `_load_calendar_definition(data: dict) -> CalendarDefinition` helper that reconstructs the full object graph; raise `ProjectLoadError` on invalid values
  - [x] 7.4 Add `_load_fantasy_datetime(data: dict, cal: CalendarDefinition) -> FantasyDateTime` helper that resolves the era name string to an `Era` object; raise `ProjectLoadError` if era name not found
  - [x] 7.5 In `load`, call `_load_calendar_definition` (defaulting to `GREGORIAN_DEFAULT` if key absent) and `_load_fantasy_datetime`; wrap `ValueError`/`KeyError` in `ProjectLoadError`

- [x] 8. Update `AppController` and `MainWindow`
  - [x] 8.1 Expose `calendar_tab` as a property on `MainWindow` returning the `CalendarTab` instance
  - [x] 8.2 In `AppController.on_load_project`, call `self._window.calendar_tab.load_from_project(project)` after loading
  - [x] 8.3 In `AppController.on_save_project`, call `self._window.calendar_tab.flush_to_project(self._project)` before saving
  - [x] 8.4 In `AppController.on_new_project`, initialise `project.calendar_definition = GREGORIAN_DEFAULT` and call `load_from_project` so the view reflects the new project

- [x] 9. Checkpoint — verify end-to-end behaviour
  - Launch the app; confirm the Gregorian default calendar renders correctly with correct weekday headers and month names.
  - Advance time past a month boundary; confirm the view navigates to the new month.
  - Save and reload a project; confirm the calendar definition and tracked date are restored exactly.
