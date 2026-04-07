# Requirements Document

## Introduction

This feature extends the custom calendar system in the TTRPG DM Tool with leap day support. The existing `MonthDefinition` model has a fixed `day_count` with no mechanism for variable-length months. This feature adds a single optional field — `leap_every_n_years` — to `MonthDefinition`, allowing any month to gain one extra day in years that are evenly divisible by that number.

This covers real-world calendars (Gregorian February gaining a 29th day every 4 years) and arbitrary fantasy calendars (e.g. "month 3 gains a day every 5 years") without introducing any new model classes. All existing behaviour is preserved: calendars without leap configuration continue to work exactly as before.

## Glossary

- **Month_Definition**: The existing data model describing a single month within a `Calendar_Definition`, including its name, base `day_count`, and the new optional `leap_every_n_years` field.
- **Effective_Day_Count**: The actual number of days in a month for a specific year — either the base `day_count`, or `day_count + 1` when `leap_every_n_years` is set and `year % leap_every_n_years == 0`.
- **Calendar_Definition**: The existing data model that fully describes the structure of a fantasy calendar.
- **Fantasy_Date_Time**: The existing point-in-time type that performs arithmetic within a `Calendar_Definition`.
- **Gregorian_Default**: The existing `CalendarDefinition` constant that recreates the standard Gregorian calendar, updated to set February's `leap_every_n_years = 4`.
- **Serializer**: The existing `src/serializer.py` component responsible for saving and loading project JSON files.
- **Project_Load_Error**: The existing exception raised by `Serializer` when a project JSON file contains invalid data.

---

## Requirements

### Requirement 1: Month Definition Extended with Leap Every N Years

**User Story:** As a DM, I want to mark any month as a leap month by specifying how often it gains an extra day, so that I can model leap years without any complicated rule objects.

#### Acceptance Criteria

1. THE Month_Definition SHALL contain an optional `leap_every_n_years` field (default `None`) expressed as a positive integer.
2. WHEN a `Month_Definition` is constructed with `leap_every_n_years` set to a value less than 2, THE Month_Definition SHALL raise a validation error.
3. WHERE a `Month_Definition` has `leap_every_n_years` set to `None`, THE Month_Definition SHALL return its base `day_count` as the effective day count for every year.
4. WHERE a `Month_Definition` has `leap_every_n_years` set and `year % leap_every_n_years == 0`, THE Month_Definition SHALL return `day_count + 1` as the effective day count for that year.
5. WHERE a `Month_Definition` has `leap_every_n_years` set and `year % leap_every_n_years != 0`, THE Month_Definition SHALL return the base `day_count` as the effective day count for that year.

---

### Requirement 2: Fantasy DateTime Arithmetic Respects Leap Days

**User Story:** As a DM, I want date arithmetic to correctly account for leap days, so that advancing time across a leap month boundary produces the right date.

#### Acceptance Criteria

1. WHEN computing `total_elapsed_days`, THE Fantasy_Date_Time SHALL use the effective day count for each month in each year.
2. WHEN `add_seconds` carries days forward across a month boundary, THE Fantasy_Date_Time SHALL use the effective day count for the current year and month to determine when the month ends.
3. WHEN `add_seconds` borrows days backward across a month boundary, THE Fantasy_Date_Time SHALL use the effective day count for the current year and month to determine how many days to borrow.
4. WHEN a `Fantasy_Date_Time` is constructed with a day equal to the leap day (i.e. `day == effective_day_count` and `effective_day_count > base_day_count`), THE Fantasy_Date_Time SHALL accept the value as valid.
5. WHEN a `Fantasy_Date_Time` is constructed with a day greater than the effective day count for its year, THE Fantasy_Date_Time SHALL raise a validation error.

---

### Requirement 3: Gregorian Default Updated with Leap Year Rule

**User Story:** As a DM, I want the default Gregorian calendar to correctly model leap years, so that February has 29 days every 4 years without any manual configuration.

#### Acceptance Criteria

1. THE Gregorian_Default SHALL set February's `leap_every_n_years` to `4`.
2. WHEN the Gregorian year is divisible by 4, THE Gregorian_Default SHALL return an effective day count of 29 for February.
3. WHEN the Gregorian year is not divisible by 4, THE Gregorian_Default SHALL return an effective day count of 28 for February.

> Note: This intentionally accepts the simplification that century years (e.g. 1900) are also leap years. This is a TTRPG tool, not a calendar library — the approximation is fine.

---

### Requirement 4: Calendar View Renders Correct Day Count for Leap Months

**User Story:** As a DM, I want the calendar grid to show the correct number of days for a leap month, so that the 29th of February (or equivalent) appears in the grid when applicable.

#### Acceptance Criteria

1. WHEN the Calendar_View renders a month for a given year, THE Calendar_View SHALL use the effective day count (accounting for `leap_every_n_years`) rather than the base `day_count` to determine the number of day cells.
2. WHEN the displayed year changes such that a previously non-leap month becomes a leap month (or vice versa), THE Calendar_View SHALL re-render the grid to reflect the updated day count.

---

### Requirement 5: Persist Leap Configuration with Project

**User Story:** As a DM, I want my leap month configuration to be saved and loaded with my project, so that it is preserved between sessions.

#### Acceptance Criteria

1. WHEN a project is saved, THE Serializer SHALL write each `Month_Definition`'s `leap_every_n_years` value to the project JSON file; months without a leap rule SHALL omit the field.
2. WHEN a project is loaded, THE Serializer SHALL reconstruct the `leap_every_n_years` value for each `Month_Definition` that has one.
3. IF a loaded project JSON file contains a `leap_every_n_years` value less than 2, THEN THE Serializer SHALL raise a `Project_Load_Error`.
4. FOR ALL valid `Calendar_Definition` objects containing leap month configuration, serializing a `Project` to JSON and then deserializing it SHALL produce a `Project` with equivalent `leap_every_n_years` values on every month.
