# Requirements Document

## Introduction

This feature replaces the hardcoded Gregorian calendar in the TTRPG DM Tool with a flexible custom DateTime/Calendar implementation. Fantasy TTRPG worlds often use calendars that differ from the real-world Gregorian calendar — with different numbers of months, days per month, days per week, hours per day, and lunar cycles. The new implementation must be configurable enough to represent any such calendar while defaulting to a Gregorian calendar recreation so that existing behaviour is preserved.

The feature introduces a `CalendarDefinition` model that describes the structure of a calendar, a `FantasyDateTime` type that represents a point in time within a given calendar, and updates to `CalendarTab`, `CalendarView`, and the serializer to use these types. The existing `CalendarDay` and `CalendarEntry` models (from the calendar-entry spec) continue to work unchanged, with dates now expressed as `FantasyDateTime` values rather than `datetime.date`.

## Glossary

- **Calendar_Definition**: A data model that fully describes the structure of a fantasy calendar, including its months, week length, weekday names, hours per day, lunar cycles, intercalary periods, and eras.
- **Month_Definition**: A data model describing a single month within a `Calendar_Definition`, including its name and number of days.
- **Lunar_Cycle**: A data model describing a moon tracked by the calendar, including its name, the number of days between phase changes, and an optional phase offset in days.
- **Fantasy_Date_Time**: A point in time expressed within a specific `Calendar_Definition`, storing year, month index, day, hour, minute, second, and an optional era reference.
- **Calendar_Tab**: The existing PyQt6 tab widget that owns the calendar view and day detail sidebar (see calendar-tab spec).
- **Calendar_View**: The existing monthly grid widget inside `Calendar_Tab` (see calendar-tab spec).
- **Day_Cell**: A single clickable cell in the calendar grid representing one day (see calendar-tab spec).
- **Tracked_Date**: The in-game date and time maintained by the DM, now stored as a `Fantasy_Date_Time`.
- **Gregorian_Default**: The `Calendar_Definition` that recreates the standard Gregorian calendar, used as the application default.
- **Serializer**: The existing `src/serializer.py` component responsible for saving and loading project JSON files.
- **Project**: The top-level data model that owns all campaign data, including the active `Calendar_Definition`.
- **Intercalary_Period**: A named block of days that does not belong to any month, inserted at a defined position within the year (after a specified month index). Intercalary days are counted in day arithmetic and day-of-week calculations but are not part of any month's day count.
- **Era**: A named time period within a `Calendar_Definition` that has a starting year and a direction (ascending or descending). Ascending eras count years upward (like AD); descending eras count years downward (like BC).

---

## Requirements

### Requirement 1: Calendar Definition Model

**User Story:** As a DM, I want to define a custom calendar with configurable months, week length, and hours per day, so that I can represent the calendar system of any fantasy world.

#### Acceptance Criteria

1. THE Calendar_Definition SHALL contain a list of one or more `Month_Definition` objects, with a minimum of 1 month and a maximum of 30 months per year.
2. THE Calendar_Definition SHALL contain a week length, expressed as the number of days per week, with a minimum of 1 and a maximum of 20.
3. THE Calendar_Definition SHALL contain a hours-per-day value with a minimum of 1 and a maximum of 99.
4. THE Calendar_Definition SHALL contain a name string that uniquely identifies the calendar.
5. THE Calendar_Definition SHALL contain a list of zero or more `Lunar_Cycle` objects.
6. THE Calendar_Definition SHALL contain a list of weekday name strings whose length equals the week length (e.g., ["Sunday", "Monday", ...] for a 7-day week).
7. THE Calendar_Definition SHALL contain a list of zero or more `Intercalary_Period` objects.
8. THE Calendar_Definition SHALL contain a list of zero or more `Era` objects.
9. WHEN a `Calendar_Definition` is constructed with fewer than 1 or more than 30 months, THE Calendar_Definition SHALL raise a validation error.
10. WHEN a `Calendar_Definition` is constructed with a week length outside the range 1–20, THE Calendar_Definition SHALL raise a validation error.
11. WHEN a `Calendar_Definition` is constructed with an hours-per-day value outside the range 1–99, THE Calendar_Definition SHALL raise a validation error.
12. WHEN a `Calendar_Definition` is constructed with a weekday name list whose length does not equal the week length, THE Calendar_Definition SHALL raise a validation error.

---

### Requirement 2: Month Definition Model

**User Story:** As a DM, I want each month to have its own name and day count, so that I can model months like February that have a non-uniform number of days.

#### Acceptance Criteria

1. THE Month_Definition SHALL contain a name string.
2. THE Month_Definition SHALL contain a day count with a minimum of 5 and a maximum of 100.
3. WHEN a `Month_Definition` is constructed with a day count outside the range 5–100, THE Month_Definition SHALL raise a validation error.

---

### Requirement 3: Lunar Cycle Model

**User Story:** As a DM, I want to track one or more moons with configurable phase-change intervals, so that I can incorporate lunar events into my campaign.

#### Acceptance Criteria

1. THE Lunar_Cycle SHALL contain a name string identifying the moon.
2. THE Lunar_Cycle SHALL contain a phase-change interval expressed as a positive integer number of days (minimum 1).
3. THE Lunar_Cycle SHALL contain an optional integer day offset (default 0) that shifts the starting phase.
4. WHEN a `Lunar_Cycle` is constructed with a phase-change interval less than 1, THE Lunar_Cycle SHALL raise a validation error.
5. WHEN calculating the lunar phase for a given day, THE Lunar_Cycle SHALL add the phase offset to the total elapsed days before computing the phase index.

---

### Requirement 4: Fantasy DateTime Model

**User Story:** As a DM, I want a date/time type that operates within a custom calendar, so that all in-game time tracking respects the fantasy world's calendar structure.

#### Acceptance Criteria

1. THE Fantasy_Date_Time SHALL store a year (positive integer), a month index (1-based, within the calendar's month count), a day (1-based, within the month's day count), an hour (0-based, within the calendar's hours-per-day), a minute (0–59), a second (0–59), and an optional reference to an `Era` defined in the active `Calendar_Definition`.
2. WHEN a `Fantasy_Date_Time` is constructed with a month index outside the valid range for its `Calendar_Definition`, THE Fantasy_Date_Time SHALL raise a validation error.
3. WHEN a `Fantasy_Date_Time` is constructed with a day outside the valid range for its month, THE Fantasy_Date_Time SHALL raise a validation error.
4. WHEN a `Fantasy_Date_Time` is constructed with an hour outside the valid range for its `Calendar_Definition`, THE Fantasy_Date_Time SHALL raise a validation error.
5. WHEN a time delta in seconds is added to a `Fantasy_Date_Time`, THE Fantasy_Date_Time SHALL return a new `Fantasy_Date_Time` that correctly carries over seconds into minutes, minutes into hours, hours into days, days into months (respecting each month's individual day count and any `Intercalary_Period` days inserted between months), and months into years.
6. WHEN a time delta in seconds is subtracted from a `Fantasy_Date_Time`, THE Fantasy_Date_Time SHALL return a new `Fantasy_Date_Time` that correctly borrows across seconds, minutes, hours, days, months (respecting each month's individual day count and any `Intercalary_Period` days), and years.
7. THE Fantasy_Date_Time SHALL expose a method that returns the day-of-week index (0-based) for the date, calculated as the total elapsed days from year 1, day 1 (including any `Intercalary_Period` days) modulo the calendar's week length.

---

### Requirement 5: Gregorian Default Calendar

**User Story:** As a DM, I want the application to default to a Gregorian calendar recreation, so that existing projects continue to work without any migration.

#### Acceptance Criteria

1. THE Gregorian_Default SHALL define 12 months with the names and day counts of the standard Gregorian calendar: January (31), February (28), March (31), April (30), May (31), June (30), July (31), August (31), September (30), October (31), November (30), December (31).
2. THE Gregorian_Default SHALL define a week length of 7 with weekday names ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].
3. THE Gregorian_Default SHALL define 24 hours per day.
4. THE Gregorian_Default SHALL define no lunar cycles by default.
5. THE Gregorian_Default SHALL define two eras: a descending era named "BC" and an ascending era named "AD" with a starting year of 1.
6. WHEN the application starts with no saved project, THE Calendar_Tab SHALL initialise the Tracked_Date using the Gregorian_Default calendar and the current real-world date.

---

### Requirement 6: Calendar View Rendering with Custom Calendar

**User Story:** As a DM, I want the calendar grid to render correctly for any active `Calendar_Definition`, so that the visual layout reflects the fantasy world's month and week structure.

#### Acceptance Criteria

1. WHEN the Calendar_View renders a month, THE Calendar_View SHALL use the active `Calendar_Definition` to determine the number of days in that month and the number of columns (days per week).
2. THE Calendar_View SHALL display weekday header labels using the weekday name strings stored in the active `Calendar_Definition`.
3. WHEN the active `Calendar_Definition` changes, THE Calendar_View SHALL re-render the grid to reflect the new calendar structure.
4. THE Calendar_View SHALL display the month name from the active `Calendar_Definition`'s `Month_Definition` list in the Month_Header.

---

### Requirement 7: Tracked Date Time Adjustment with Custom Calendar

**User Story:** As a DM, I want the time adjustment buttons to work correctly with any custom calendar, so that advancing or rewinding time respects the fantasy world's day and month lengths.

#### Acceptance Criteria

1. WHEN a time adjustment button is clicked, THE Calendar_Tab SHALL add or subtract the corresponding number of seconds from the Tracked_Date using `Fantasy_Date_Time` arithmetic.
2. WHEN a time adjustment causes the Tracked_Date to move to a different month or year, THE Calendar_View SHALL navigate to display the new month.
3. THE Tracked_Date_Banner SHALL display the Tracked_Date using the month name and weekday name from the active `Calendar_Definition`, and SHALL include the era name when the Tracked_Date has an era reference.

---

### Requirement 8: Lunar Phase Display

**User Story:** As a DM, I want to see the current lunar phase for each tracked moon when viewing a day, so that I can incorporate lunar events into my storytelling.

#### Acceptance Criteria

1. WHERE the active `Calendar_Definition` contains one or more `Lunar_Cycle` objects, THE Day_Detail_Sidebar SHALL display the current phase of each moon for the selected day.
2. THE Day_Detail_Sidebar SHALL calculate the lunar phase by adding the `Lunar_Cycle`'s phase offset to the total elapsed days from the start of the calendar, dividing the result by the `Lunar_Cycle`'s phase-change interval, then mapping the remainder to one of eight standard phase names: New Moon, Waxing Crescent, First Quarter, Waxing Gibbous, Full Moon, Waning Gibbous, Last Quarter, Waning Crescent.
3. WHERE the active `Calendar_Definition` contains no `Lunar_Cycle` objects, THE Day_Detail_Sidebar SHALL display no lunar phase information.

---

### Requirement 9: Persist Calendar Definition with Project

**User Story:** As a DM, I want the active calendar definition to be saved and loaded with my project, so that my custom calendar is restored between sessions.

#### Acceptance Criteria

1. THE Project SHALL store the active `Calendar_Definition`, including all `Month_Definition` objects, `Lunar_Cycle` objects, `Intercalary_Period` objects, and `Era` objects.
2. WHEN a project is saved, THE Serializer SHALL write the full `Calendar_Definition` to the project JSON file.
3. WHEN a project is loaded, THE Serializer SHALL reconstruct the `Calendar_Definition`, all `Month_Definition` objects, `Lunar_Cycle` objects, `Intercalary_Period` objects, and `Era` objects from the project JSON file.
4. WHEN a project is loaded, THE Serializer SHALL reconstruct the Tracked_Date as a `Fantasy_Date_Time` bound to the loaded `Calendar_Definition`, including its era reference if present.
5. IF a loaded project JSON file contains no calendar definition, THEN THE Serializer SHALL initialise the project with the Gregorian_Default calendar.
6. IF a loaded project JSON file contains a `Calendar_Definition` with invalid values (e.g., month count out of range), THEN THE Serializer SHALL raise a `ProjectLoadError`.

---

### Requirement 10: Serialization Round-Trip Integrity

**User Story:** As a DM, I want my calendar data to survive a save/load cycle without any loss or corruption, so that I can trust the tool to preserve my campaign setup.

#### Acceptance Criteria

1. FOR ALL valid `Calendar_Definition` objects, serializing a `Project` containing that definition to JSON and then deserializing it SHALL produce a `Project` with an equivalent `Calendar_Definition` (same name, same month names and day counts, same week length, same weekday names, same hours per day, same lunar cycles with phase offsets, same intercalary periods, same eras).
2. FOR ALL valid `Fantasy_Date_Time` values, serializing and then deserializing a `Project` containing that value SHALL produce an equivalent `Fantasy_Date_Time` (same year, month, day, hour, minute, second, and era reference).

---

### Requirement 11: Intercalary Period Model

**User Story:** As a DM, I want to define days that fall outside any month (such as a "Year's End" festival), so that I can model calendars with intercalary periods.

#### Acceptance Criteria

1. THE Intercalary_Period SHALL contain a name string identifying the period.
2. THE Intercalary_Period SHALL contain a day count expressed as a positive integer (minimum 1).
3. THE Intercalary_Period SHALL contain a position expressed as a month index (0-based) indicating that the intercalary days are inserted after that month; a position of 0 inserts the period before the first month.
4. WHEN a `Calendar_Definition` contains one or more `Intercalary_Period` objects, THE Fantasy_Date_Time arithmetic SHALL include intercalary days in the total elapsed day count when crossing the position boundary.
5. WHEN a `Calendar_Definition` contains one or more `Intercalary_Period` objects, THE Fantasy_Date_Time day-of-week calculation SHALL include intercalary days in the total elapsed day count.
6. WHEN an `Intercalary_Period` is constructed with a day count less than 1, THE Intercalary_Period SHALL raise a validation error.

---

### Requirement 12: Era Model

**User Story:** As a DM, I want to define named eras with ascending or descending year counts, so that I can represent historical epochs like "Before the Sundering" or "Age of Mortals" in my world's calendar.

#### Acceptance Criteria

1. THE Era SHALL contain a name string identifying the era.
2. THE Era SHALL contain a starting year expressed as a positive integer.
3. THE Era SHALL contain a direction value of either ascending (years count upward) or descending (years count downward).
4. WHERE a `Fantasy_Date_Time` has an era reference, THE Tracked_Date_Banner SHALL include the era name when displaying the date.
5. WHERE a `Fantasy_Date_Time` has no era reference, THE Tracked_Date_Banner SHALL display the date without an era name.
