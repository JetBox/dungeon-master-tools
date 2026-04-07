# Design Document: Leap Day Support

## Overview

This feature extends `MonthDefinition` with a single optional field — `leap_every_n_years: int | None` — that allows any month to gain one extra day in years evenly divisible by that number. All existing behaviour is preserved: calendars without leap configuration continue to work exactly as before.

The change touches four areas:

1. **`MonthDefinition`** — new field + `effective_day_count(year)` helper
2. **`FantasyDateTime`** — `__post_init__`, `total_elapsed_days`, and `add_seconds` use effective day count
3. **`GREGORIAN_DEFAULT`** — February gets `leap_every_n_years=4`
4. **`CalendarView._rebuild_grid`** — uses effective day count for the displayed year

Serialization requires no structural changes: `dataclasses.asdict` serialises the new integer field automatically, and `_load_calendar_definition` already passes `**m` to `MonthDefinition(...)`, so the field is reconstructed for free.

---

## Architecture

No new classes or modules are introduced. The change is additive: one new field on an existing dataclass, one new helper method, and targeted updates to the three call-sites that previously read `month.day_count` directly.

```
MonthDefinition.effective_day_count(year)
        │
        ├── FantasyDateTime.__post_init__   (validation)
        ├── FantasyDateTime.total_elapsed_days
        ├── FantasyDateTime.add_seconds
        └── CalendarView._rebuild_grid
```

---

## Components and Interfaces

### `MonthDefinition` (src/models.py)

New field and helper method:

```python
@dataclass
class MonthDefinition:
    name: str
    day_count: int                        # base day count; 5–100
    leap_every_n_years: int | None = None # optional; must be >= 2 if set

    def __post_init__(self):
        if not (5 <= self.day_count <= 100):
            raise ValueError(f"day_count must be between 5 and 100, got {self.day_count}")
        if self.leap_every_n_years is not None and self.leap_every_n_years < 2:
            raise ValueError(
                f"leap_every_n_years must be >= 2 if set, got {self.leap_every_n_years}"
            )

    def effective_day_count(self, year: int) -> int:
        """Return the actual number of days in this month for the given year."""
        if self.leap_every_n_years is not None and year % self.leap_every_n_years == 0:
            return self.day_count + 1
        return self.day_count
```

`effective_day_count` is the single source of truth for leap logic. All other components call this method rather than reading `day_count` directly.

### `FantasyDateTime` (src/models.py)

Three targeted changes — no new public API:

**`__post_init__` validation** — replace `month.day_count` with `month.effective_day_count(self.year)`:

```python
max_day = self.calendar.months[self.month - 1].effective_day_count(self.year)
if not (1 <= self.day <= max_day):
    raise ValueError(f"day must be between 1 and {max_day}, got {self.day}")
```

**`total_elapsed_days`** — replace `month.day_count` with `month.effective_day_count(year)` in the year/month iteration loops:

```python
# Complete years before self.year
for yr in range(1, self.year):
    for mi, month in enumerate(cal.months):
        total += month.effective_day_count(yr) + intercalary_days_after(mi)

# Complete months before self.month in self.year
for mi in range(self.month - 1):
    total += cal.months[mi].effective_day_count(self.year) + intercalary_days_after(mi)
```

**`add_seconds` forward/backward carry** — replace `cal.months[month - 1].day_count` with `cal.months[month - 1].effective_day_count(year)` at every boundary check:

```python
# Forward carry
while day > cal.months[month - 1].effective_day_count(year):
    day -= cal.months[month - 1].effective_day_count(year)
    ...

# Backward borrow
    day += cal.months[month - 1].effective_day_count(year)
```

### `GREGORIAN_DEFAULT` (src/models.py)

February's definition gains the leap field:

```python
MonthDefinition("February", 28, leap_every_n_years=4)
```

All other months are unchanged (their `leap_every_n_years` defaults to `None`).

### `CalendarView._rebuild_grid` (src/views/calendar_tab.py)

Replace the single line that reads `month_def.day_count` with `month_def.effective_day_count(self._year)`:

```python
day_count = month_def.effective_day_count(self._year)
```

The grid automatically re-renders whenever `_rebuild_grid` is called (on month/year navigation), so Requirement 4.2 is satisfied without any additional signal wiring.

### `Serializer` (src/serializer.py)

No code changes required.

- **Save**: `dataclasses.asdict(project)` recursively converts all dataclass fields. `leap_every_n_years` is an `int | None`, so it serialises as a JSON integer or is omitted when `None` (Python's `json.dump` serialises `None` as `null`; the field will be present as `null` or as an integer).
- **Load**: `_load_calendar_definition` already does `MonthDefinition(**m)` for each month dict. When the JSON contains `"leap_every_n_years": 4`, it is passed as a keyword argument. When the field is absent or `null`, Python's default `None` applies. `MonthDefinition.__post_init__` raises `ValueError` for values < 2, which is caught by the existing `except (KeyError, ValueError)` handler and re-raised as `ProjectLoadError`.

---

## Data Models

### `MonthDefinition` JSON representation

Months without a leap rule omit the field (or store `null`); months with a leap rule store the integer:

```json
{
    "months": [
        {"name": "January",  "day_count": 31},
        {"name": "February", "day_count": 28, "leap_every_n_years": 4},
        {"name": "March",    "day_count": 31}
    ]
}
```

### Full project JSON (excerpt)

```json
{
    "name": "My Campaign",
    "version": "1.0",
    "calendar_definition": {
        "name": "Gregorian",
        "months": [
            {"name": "January",  "day_count": 31, "leap_every_n_years": null},
            {"name": "February", "day_count": 28, "leap_every_n_years": 4},
            {"name": "March",    "day_count": 31, "leap_every_n_years": null}
        ],
        "week_length": 7,
        "weekday_names": ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],
        "hours_per_day": 24,
        "lunar_cycles": [],
        "intercalary_periods": [],
        "eras": [
            {"name": "BC", "starting_year": 1, "direction": "descending"},
            {"name": "AD", "starting_year": 1, "direction": "ascending"}
        ]
    },
    "tracked_date": {
        "year": 2024, "month": 2, "day": 29,
        "hour": 0, "minute": 0, "second": 0, "era": "AD"
    },
    "calendar_days": []
}
```

### Effective day count logic (summary)

| `leap_every_n_years` | `year % leap_every_n_years` | effective day count |
|---|---|---|
| `None` | — | `day_count` |
| set | `== 0` | `day_count + 1` |
| set | `!= 0` | `day_count` |


---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

**Property reflection**: The prework identified several overlapping properties. After consolidation:
- 1.4 and 1.5 (leap vs non-leap effective day count) are combined into one comprehensive property covering both cases.
- 2.1, 2.2, and 2.3 (arithmetic uses effective day count) are all validated by the round-trip property.
- 4.2 (re-render on year change) is subsumed by 4.1 (cell count equals effective day count for any year).
- 5.1 and 5.2 (save/load leap field) are subsumed by 5.4 (round-trip).

### Property 1: effective_day_count respects leap_every_n_years

*For any* valid `MonthDefinition` with `leap_every_n_years` set to `n >= 2`, and for any positive integer year, `effective_day_count(year)` SHALL return `day_count + 1` when `year % n == 0` and `day_count` otherwise. When `leap_every_n_years` is `None`, `effective_day_count(year)` SHALL return `day_count` for every year.

**Validates: Requirements 1.3, 1.4, 1.5**

### Property 2: leap_every_n_years < 2 is rejected

*For any* integer value less than 2, constructing a `MonthDefinition` with `leap_every_n_years` set to that value SHALL raise a `ValueError`.

**Validates: Requirements 1.2**

### Property 3: FantasyDateTime rejects day > effective_day_count

*For any* valid `CalendarDefinition` containing a leap month, and for any non-leap year, constructing a `FantasyDateTime` with `day` equal to `base_day_count + 1` for that month SHALL raise a `ValueError`; constructing with `day` equal to `base_day_count + 1` in a leap year SHALL succeed.

**Validates: Requirements 2.4, 2.5**

### Property 4: add_seconds round-trip across leap boundaries

*For any* valid `FantasyDateTime` in a calendar with at least one leap month, and for any integer delta in seconds, applying `add_seconds(delta)` followed by `add_seconds(-delta)` SHALL return a `FantasyDateTime` equivalent to the original.

**Validates: Requirements 2.1, 2.2, 2.3**

### Property 5: CalendarView cell count equals effective_day_count

*For any* `CalendarDefinition` containing a leap month and any year (leap or non-leap), the number of `DayCell` widgets rendered by `CalendarView._rebuild_grid` SHALL equal `month.effective_day_count(year)` for the displayed month.

**Validates: Requirements 4.1, 4.2**

### Property 6: Serialization round-trip preserves leap_every_n_years

*For any* valid `CalendarDefinition` containing months with `leap_every_n_years` set, serializing a `Project` to JSON and then deserializing it SHALL produce a `Project` where every month's `leap_every_n_years` value is identical to the original.

**Validates: Requirements 5.1, 5.2, 5.4**

### Property 7: Serializer rejects leap_every_n_years < 2 on load

*For any* integer value less than 2, a project JSON file containing that value as `leap_every_n_years` for any month SHALL cause `Serializer.load` to raise a `ProjectLoadError`.

**Validates: Requirements 5.3**

---

## Error Handling

| Scenario | Handling |
|---|---|
| `MonthDefinition` constructed with `leap_every_n_years < 2` | `ValueError` raised in `__post_init__` |
| `FantasyDateTime` constructed with `day > effective_day_count(year)` | `ValueError` raised in `__post_init__` |
| Project JSON contains `leap_every_n_years` value less than 2 | `Serializer.load` raises `ProjectLoadError` (caught by existing `except (KeyError, ValueError)` handler in `_load_calendar_definition`) |
| Project JSON month has no `leap_every_n_years` key | `MonthDefinition(**m)` uses default `None`; no error |
| Project JSON month has `leap_every_n_years: null` | `MonthDefinition(**m)` receives `None`; no error |

---

## Testing Strategy

Per the project testing policy, unit tests are not required. The correctness properties above serve as the specification for any future automated testing.

If tests are added, the recommended approach is:

- Use `pytest` with `hypothesis` for property-based testing
- Each property test should run a minimum of 100 iterations
- Tag each test referencing the design property, e.g.:
  `# Feature: leap-day-support, Property 4: add_seconds round-trip across leap boundaries`

**Property test targets**:
- Property 1: Generate random `(day_count, leap_every_n_years, year)` tuples; verify `effective_day_count` returns correct value for both leap and non-leap years, and always returns `day_count` when `leap_every_n_years` is `None`
- Property 2: Generate random integers < 2; verify `MonthDefinition` raises `ValueError`
- Property 3: Generate random calendars with a leap month; for non-leap years verify `day = base + 1` raises `ValueError`; for leap years verify it succeeds
- Property 4: Generate random valid `FantasyDateTime` values in calendars with leap months and random integer deltas; verify `add_seconds(delta)` then `add_seconds(-delta)` returns the original
- Property 5: Generate random `CalendarDefinition` objects with leap months; render `CalendarView` for both leap and non-leap years; verify cell count equals `effective_day_count(year)`
- Property 6: Generate random valid `CalendarDefinition` objects with leap months; serialize then deserialize; verify all `leap_every_n_years` values match
- Property 7: Generate random integers < 2; construct project JSON with that value; verify `Serializer.load` raises `ProjectLoadError`
