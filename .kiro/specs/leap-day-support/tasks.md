# Implementation Plan: Leap Day Support

## Overview

Extend `MonthDefinition` with an optional `leap_every_n_years` field and propagate `effective_day_count(year)` through `FantasyDateTime` arithmetic, `GREGORIAN_DEFAULT`, and `CalendarView` rendering.

## Tasks

- [x] 1. Extend `MonthDefinition` with `leap_every_n_years` and `effective_day_count`
  - Add `leap_every_n_years: int | None = None` field to `MonthDefinition` in `src/models.py`
  - Extend `__post_init__` to raise `ValueError` when `leap_every_n_years` is set and less than 2
  - Implement `effective_day_count(self, year: int) -> int` method returning `day_count + 1` when `year % leap_every_n_years == 0`, else `day_count`; return `day_count` when field is `None`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.1 Write property test for `effective_day_count` correctness
    - **Property 1: effective_day_count respects leap_every_n_years**
    - Generate random `(day_count, leap_every_n_years, year)` tuples; verify leap and non-leap results, and `None` always returns `day_count`
    - **Validates: Requirements 1.3, 1.4, 1.5**

  - [ ]* 1.2 Write property test for `leap_every_n_years < 2` rejection
    - **Property 2: leap_every_n_years < 2 is rejected**
    - Generate random integers < 2; verify `MonthDefinition` raises `ValueError`
    - **Validates: Requirements 1.2**

- [x] 2. Update `FantasyDateTime` to use `effective_day_count`
  - In `__post_init__`, replace `month.day_count` with `month.effective_day_count(self.year)` for the `max_day` validation
  - In `total_elapsed_days`, replace `month.day_count` with `month.effective_day_count(yr)` in the year loop and `month.effective_day_count(self.year)` in the month loop
  - In `add_seconds`, replace every `cal.months[month - 1].day_count` boundary check with `cal.months[month - 1].effective_day_count(year)` in both the forward carry and backward borrow loops
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 2.1 Write property test for `FantasyDateTime` leap day validation
    - **Property 3: FantasyDateTime rejects day > effective_day_count**
    - Generate random calendars with a leap month; verify `day = base + 1` raises `ValueError` in non-leap years and succeeds in leap years
    - **Validates: Requirements 2.4, 2.5**

  - [ ]* 2.2 Write property test for `add_seconds` round-trip across leap boundaries
    - **Property 4: add_seconds round-trip across leap boundaries**
    - Generate random valid `FantasyDateTime` values in calendars with leap months and random integer deltas; verify `add_seconds(delta)` then `add_seconds(-delta)` returns the original
    - **Validates: Requirements 2.1, 2.2, 2.3**

- [x] 3. Checkpoint — Ensure all tests pass, ask the user if questions arise.

- [x] 4. Update `GREGORIAN_DEFAULT` with February leap rule
  - Change `MonthDefinition("February", 28)` to `MonthDefinition("February", 28, leap_every_n_years=4)` in `src/models.py`
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 5. Update `CalendarView._rebuild_grid` to use `effective_day_count`
  - In `src/views/calendar_tab.py`, replace `day_count = month_def.day_count` with `day_count = month_def.effective_day_count(self._year)`
  - _Requirements: 4.1, 4.2_

  - [ ]* 5.1 Write property test for `CalendarView` cell count
    - **Property 5: CalendarView cell count equals effective_day_count**
    - Generate random `CalendarDefinition` objects with leap months; render `CalendarView` for both leap and non-leap years; verify `len(_cells)` equals `month.effective_day_count(year)`
    - **Validates: Requirements 4.1, 4.2**

- [x] 6. Verify serialization handles `leap_every_n_years`
  - Confirm `dataclasses.asdict` in `Serializer.save` serialises the new field automatically (no code change needed)
  - Confirm `MonthDefinition(**m)` in `_load_calendar_definition` reconstructs the field from JSON (no code change needed)
  - Confirm the existing `except (KeyError, ValueError)` handler in `_load_calendar_definition` propagates `ValueError` from `MonthDefinition.__post_init__` as `ProjectLoadError` (no code change needed)
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 6.1 Write property test for serialization round-trip
    - **Property 6: Serialization round-trip preserves leap_every_n_years**
    - Generate random valid `CalendarDefinition` objects with leap months; serialize then deserialize; verify all `leap_every_n_years` values match
    - **Validates: Requirements 5.1, 5.2, 5.4**

  - [ ]* 6.2 Write property test for `Serializer.load` rejecting invalid `leap_every_n_years`
    - **Property 7: Serializer rejects leap_every_n_years < 2 on load**
    - Generate random integers < 2; construct project JSON with that value; verify `Serializer.load` raises `ProjectLoadError`
    - **Validates: Requirements 5.3**

- [x] 7. Final checkpoint — Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped per the project testing policy
- Property tests use `pytest` + `hypothesis`; tag each test with its property number, e.g. `# Feature: leap-day-support, Property 1: effective_day_count respects leap_every_n_years`
- Task 6 requires no code changes to `src/serializer.py`; it is a verification step only
