# Design Document: Custom Calendar

## Overview

This feature replaces the hardcoded Gregorian calendar in the TTRPG DM Tool with a fully configurable calendar system. It introduces:

- `CalendarDefinition`, `MonthDefinition`, `LunarCycle`, `IntercalaryPeriod`, and `Era` data models in `src/models.py`
- `FantasyDateTime` — a point-in-time type that performs arithmetic within any `CalendarDefinition`
- A `GREGORIAN_DEFAULT` constant that recreates the standard Gregorian calendar
- Updates to `CalendarView` and `DayDetailSidebar` in `src/views/calendar_tab.py` to render using the active `CalendarDefinition`
- Updates to `Serializer` in `src/serializer.py` to persist and restore the full calendar definition and tracked date
- Updates to `Project` in `src/models.py` to own the active `CalendarDefinition` and tracked `FantasyDateTime`

The existing `CalendarDay` / `CalendarEntry` models (from the calendar-entry spec) are preserved; their `date` field changes type from `datetime.date` to `FantasyDateTime`.

---

## Architecture

The feature follows the existing MVC-lite pattern:

```
AppController
  └── MainWindow
        └── CalendarTab
              ├── CalendarView          ← renders grid using CalendarDefinition
              └── DayDetailSidebar      ← shows lunar phases per LunarCycle
```

`CalendarDefinition` is owned by `Project`. `CalendarTab` holds a reference to the active `CalendarDefinition` and a `FantasyDateTime` for the tracked date. When a project is loaded, `AppController` pushes the new definition and tracked date into `CalendarTab`.

```
Project
  ├── calendar_definition: CalendarDefinition
  ├── tracked_date: FantasyDateTime
  └── calendar_days: list[CalendarDay]   (unchanged from calendar-entry spec)
```

---

## Components and Interfaces

### `MonthDefinition` (src/models.py)

```python
@dataclass
class MonthDefinition:
    name: str
    day_count: int  # 5–100; validated in __post_init__
```

### `LunarCycle` (src/models.py)

```python
@dataclass
class LunarCycle:
    name: str
    phase_interval: int   # days between phase changes; minimum 1
    phase_offset: int = 0 # optional shift in days; default 0
```

### `IntercalaryPeriod` (src/models.py)

```python
@dataclass
class IntercalaryPeriod:
    name: str
    day_count: int   # minimum 1
    after_month: int # 0-based month index; 0 = before first month
```

### `Era` (src/models.py)

```python
from enum import Enum

class EraDirection(Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"

@dataclass
class Era:
    name: str
    starting_year: int        # positive integer
    direction: EraDirection
```

### `CalendarDefinition` (src/models.py)

```python
@dataclass
class CalendarDefinition:
    name: str
    months: list[MonthDefinition]          # 1–30
    week_length: int                        # 1–20
    weekday_names: list[str]               # len == week_length
    hours_per_day: int                      # 1–99
    lunar_cycles: list[LunarCycle] = field(default_factory=list)
    intercalary_periods: list[IntercalaryPeriod] = field(default_factory=list)
    eras: list[Era] = field(default_factory=list)
```

Validation in `__post_init__`:
- `1 <= len(months) <= 30`
- `1 <= week_length <= 20`
- `len(weekday_names) == week_length`
- `1 <= hours_per_day <= 99`

### `FantasyDateTime` (src/models.py)

```python
@dataclass
class FantasyDateTime:
    calendar: CalendarDefinition
    year: int           # positive integer
    month: int          # 1-based
    day: int            # 1-based
    hour: int           # 0-based
    minute: int         # 0–59
    second: int         # 0–59
    era: Era | None = None
```

Key methods:

```python
def add_seconds(self, delta: int) -> "FantasyDateTime":
    """Return a new FantasyDateTime with delta seconds applied (positive or negative)."""

def day_of_week(self) -> int:
    """Return 0-based weekday index: total_elapsed_days % week_length."""

def total_elapsed_days(self) -> int:
    """Sum of all days from year 1 day 1 through self, including intercalary days."""
```

`add_seconds` handles carry/borrow across seconds → minutes → hours → days → months (respecting each month's `day_count` and any `IntercalaryPeriod` days inserted between months) → years.

#### Intercalary Day Handling

Intercalary periods are inserted after a specific month index (`after_month`). When advancing or rewinding days across a month boundary, the arithmetic checks whether an intercalary period is positioned at that boundary and includes its `day_count` in the elapsed total.

For `total_elapsed_days`, the algorithm iterates year by year and month by month, adding each month's `day_count` plus any intercalary days positioned after that month.

#### Lunar Phase Calculation

```python
def lunar_phase(self, cycle: LunarCycle) -> str:
    """Return one of 8 phase name strings for the given LunarCycle."""
    elapsed = self.total_elapsed_days() + cycle.phase_offset
    index = (elapsed // cycle.phase_interval) % 8
    return PHASE_NAMES[index]

PHASE_NAMES = [
    "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
    "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
]
```

### `GREGORIAN_DEFAULT` (src/models.py)

A module-level constant:

```python
GREGORIAN_DEFAULT = CalendarDefinition(
    name="Gregorian",
    months=[
        MonthDefinition("January", 31), MonthDefinition("February", 28),
        MonthDefinition("March", 31),   MonthDefinition("April", 30),
        MonthDefinition("May", 31),     MonthDefinition("June", 30),
        MonthDefinition("July", 31),    MonthDefinition("August", 31),
        MonthDefinition("September", 30), MonthDefinition("October", 31),
        MonthDefinition("November", 30), MonthDefinition("December", 31),
    ],
    week_length=7,
    weekday_names=["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    hours_per_day=24,
    eras=[
        Era("BC", starting_year=1, direction=EraDirection.DESCENDING),
        Era("AD", starting_year=1, direction=EraDirection.ASCENDING),
    ],
)
```

### `Project` (src/models.py — updated)

```python
@dataclass
class Project:
    name: str
    version: str = "1.0"
    calendar_definition: CalendarDefinition = field(default_factory=lambda: GREGORIAN_DEFAULT)
    tracked_date: FantasyDateTime | None = None
    calendar_days: list[CalendarDay] = field(default_factory=list)
```

`tracked_date` is `None` until the project is first opened; `CalendarTab.__init__` initialises it from the real-world date when `None`.

### `CalendarView` (src/views/calendar_tab.py — updated)

`CalendarView` accepts a `CalendarDefinition` and uses it to:
- Determine the number of columns (`week_length`)
- Render weekday header labels from `weekday_names`
- Determine the number of days in the displayed month from `months[month_index].day_count`
- Display the month name from `months[month_index].name`

Navigation (`_go_prev_month` / `_go_next_month`) wraps at `len(calendar.months)` instead of 12.

`refresh_states` accepts a `FantasyDateTime` instead of `datetime.datetime`.

### `DayDetailSidebar` (src/views/calendar_tab.py — updated)

When a day is selected, the sidebar calls `FantasyDateTime.lunar_phase(cycle)` for each `LunarCycle` in the active `CalendarDefinition` and displays the result. If there are no lunar cycles, no lunar section is shown.

### `CalendarTab` (src/views/calendar_tab.py — updated)

```python
class CalendarTab(QWidget):
    def __init__(self, calendar_def: CalendarDefinition | None = None, parent=None) -> None: ...

    def load_from_project(self, project: Project) -> None:
        """Set active calendar definition and tracked date from project."""

    def flush_to_project(self, project: Project) -> None:
        """Write tracked_date and calendar_days back to project before save."""
```

`_on_time_adjusted` now calls `self._tracked_date.add_seconds(delta)` instead of `timedelta`.

### `Serializer` (src/serializer.py — updated)

Serialization uses `dataclasses.asdict`. The `save` method applies a `_to_serializable` pass to convert `Enum` values to their `.value` strings (since `asdict` does not handle enums automatically).

`load` reconstructs the full object graph:

```python
def _load_calendar_definition(data: dict) -> CalendarDefinition: ...
def _load_fantasy_datetime(data: dict, cal: CalendarDefinition) -> FantasyDateTime: ...
```

If `calendar_definition` is absent from the JSON, `GREGORIAN_DEFAULT` is used. If present but invalid, a `ProjectLoadError` is raised.

---

## Data Models

### JSON representation

```json
{
    "name": "My Campaign",
    "version": "1.0",
    "calendar_definition": {
        "name": "Gregorian",
        "months": [
            {"name": "January", "day_count": 31},
            {"name": "February", "day_count": 28}
        ],
        "week_length": 7,
        "weekday_names": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "hours_per_day": 24,
        "lunar_cycles": [],
        "intercalary_periods": [],
        "eras": [
            {"name": "BC", "starting_year": 1, "direction": "descending"},
            {"name": "AD", "starting_year": 1, "direction": "ascending"}
        ]
    },
    "tracked_date": {
        "year": 2025,
        "month": 6,
        "day": 9,
        "hour": 0,
        "minute": 0,
        "second": 0,
        "era": "AD"
    },
    "calendar_days": []
}
```

`era` in `tracked_date` is stored as the era name string; on load it is resolved by looking up the name in the loaded `CalendarDefinition.eras` list.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: CalendarDefinition validation rejects out-of-range inputs

*For any* combination of month list length, week length, hours-per-day, and weekday name list, constructing a `CalendarDefinition` should succeed if and only if all values are within their valid ranges (1–30 months, 1–20 week length, 1–99 hours-per-day, `len(weekday_names) == week_length`), and raise a `ValueError` otherwise.

**Validates: Requirements 1.1, 1.2, 1.3, 1.6, 1.9, 1.10, 1.11, 1.12**

### Property 2: MonthDefinition and IntercalaryPeriod validation

*For any* integer `day_count`, constructing a `MonthDefinition` should succeed if and only if `5 <= day_count <= 100`, and constructing an `IntercalaryPeriod` should succeed if and only if `day_count >= 1`; both should raise `ValueError` for out-of-range values.

**Validates: Requirements 2.2, 2.3, 11.2, 11.6**

### Property 3: LunarCycle phase calculation

*For any* total elapsed day count, phase offset, and phase interval (>= 1), the computed phase index should equal `(elapsed_days + phase_offset) // phase_interval % 8`, mapping to one of the 8 standard phase name strings.

**Validates: Requirements 3.2, 3.4, 3.5, 8.2**

### Property 4: FantasyDateTime arithmetic round-trip

*For any* valid `FantasyDateTime` and any integer delta in seconds, adding `delta` seconds and then subtracting `delta` seconds should return a `FantasyDateTime` equivalent to the original, correctly carrying and borrowing across all time units including intercalary days.

**Validates: Requirements 4.5, 4.6, 11.4**

### Property 5: FantasyDateTime add(0) is identity

*For any* valid `FantasyDateTime`, adding zero seconds should return a value equal to the original.

**Validates: Requirements 4.5**

### Property 6: day_of_week advances correctly with week length

*For any* valid `FantasyDateTime` and its active `CalendarDefinition`, advancing the date by exactly `week_length` days should produce a `FantasyDateTime` with the same `day_of_week` index, and `day_of_week` should equal `total_elapsed_days() % week_length`.

**Validates: Requirements 4.7, 11.5**

### Property 7: CalendarView grid matches CalendarDefinition structure

*For any* `CalendarDefinition` and any valid month index, the rendered `CalendarView` grid should have exactly `week_length` columns, display weekday header labels matching `weekday_names`, display the month name matching `months[index].name`, and contain exactly `months[index].day_count` day cells.

**Validates: Requirements 6.1, 6.2, 6.4**

### Property 8: Tracked date banner contains correct names

*For any* valid `FantasyDateTime`, the formatted banner string should contain the month name from `CalendarDefinition.months[month-1].name`, the weekday name from `CalendarDefinition.weekday_names[day_of_week()]`, and the era name when the `FantasyDateTime` has an era reference.

**Validates: Requirements 7.3, 12.4**

### Property 9: Serialization round-trip preserves CalendarDefinition

*For any* valid `CalendarDefinition` (including all months, lunar cycles, intercalary periods, and eras), serializing a `Project` containing it to JSON and then deserializing should produce a `Project` with an equivalent `CalendarDefinition` — same name, same month names and day counts, same week length, same weekday names, same hours-per-day, same lunar cycles with phase offsets, same intercalary periods, same eras.

**Validates: Requirements 9.1, 9.2, 9.3, 10.1**

### Property 10: Serialization round-trip preserves FantasyDateTime

*For any* valid `FantasyDateTime` (including era reference when present), serializing and then deserializing a `Project` containing that value should produce an equivalent `FantasyDateTime` — same year, month, day, hour, minute, second, and era reference.

**Validates: Requirements 9.4, 10.2**

---

## Error Handling

| Scenario | Handling |
|---|---|
| `CalendarDefinition` constructed with month count outside 1–30 | `ValueError` raised in `__post_init__` |
| `CalendarDefinition` constructed with week length outside 1–20 | `ValueError` raised in `__post_init__` |
| `CalendarDefinition` constructed with hours-per-day outside 1–99 | `ValueError` raised in `__post_init__` |
| `CalendarDefinition` constructed with `len(weekday_names) != week_length` | `ValueError` raised in `__post_init__` |
| `MonthDefinition` constructed with day_count outside 5–100 | `ValueError` raised in `__post_init__` |
| `LunarCycle` constructed with phase_interval < 1 | `ValueError` raised in `__post_init__` |
| `IntercalaryPeriod` constructed with day_count < 1 | `ValueError` raised in `__post_init__` |
| `FantasyDateTime` constructed with out-of-range month, day, or hour | `ValueError` raised in `__post_init__` |
| Project JSON missing `calendar_definition` key | `Serializer.load` uses `GREGORIAN_DEFAULT`; no error |
| Project JSON contains invalid `CalendarDefinition` values | `Serializer.load` raises `ProjectLoadError` |
| Project JSON contains malformed `tracked_date` | `Serializer.load` raises `ProjectLoadError` |
| Era name in `tracked_date` not found in loaded `CalendarDefinition.eras` | `Serializer.load` raises `ProjectLoadError` |

---

## Testing Strategy

Per the project testing policy, unit tests are not required. The correctness properties above serve as the specification for any future automated testing.

If tests are added, the recommended approach is:

- Use `pytest` with `hypothesis` for property-based testing
- Use `pytest-qt` for PyQt6 widget tests
- Each property test should run a minimum of 100 iterations
- Tag each test referencing the design property, e.g.:
  `# Feature: custom-calendar, Property 9: serialization round-trip preserves CalendarDefinition`

**Property test targets**:
- Property 1: Generate random (month count, week_length, hours_per_day, weekday_names) tuples; verify construction succeeds/fails at boundaries
- Property 2: Generate random day_count integers; verify MonthDefinition and IntercalaryPeriod accept/reject correctly
- Property 3: Generate random (elapsed_days, phase_offset, phase_interval) tuples; verify phase index formula and name mapping
- Property 4: Generate random valid FantasyDateTime values and integer deltas; verify add(delta) then add(-delta) returns original
- Property 5: Generate random valid FantasyDateTime values; verify add(0) returns equivalent value
- Property 6: Generate random valid FantasyDateTime values; verify day_of_week formula and week_length-day advance invariant
- Property 7: Generate random CalendarDefinitions; render CalendarView; verify column count, header labels, month name, and day cell count
- Property 8: Generate random FantasyDateTime values; verify banner string contains correct month name, weekday name, and era name
- Property 9: Generate random valid CalendarDefinition objects; serialize then deserialize; verify all fields match
- Property 10: Generate random valid FantasyDateTime values; serialize then deserialize; verify all fields match
