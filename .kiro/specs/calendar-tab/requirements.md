# Requirements Document

## Introduction

The Calendar Tab is a new tab in the TTRPG DM Tool that provides in-game time tracking for the Dungeon Master. It displays a monthly calendar view of the current real-world calendar (with custom fantasy calendars planned for a future iteration). The DM maintains a tracked in-game date/time that drives visual distinctions between past, present, and future days. Clicking a day opens a sidebar with day-specific details (placeholder for future content).

## Glossary

- **Calendar_Tab**: The PyQt6 tab widget containing the calendar view and day detail sidebar.
- **Calendar_View**: The left-side panel displaying the monthly grid of days.
- **Day_Cell**: A single clickable cell in the calendar grid representing one calendar day.
- **Tracked_Date**: The in-game date and time maintained by the DM, used as the reference point for past/present/future calculations. This is not real-time; it is manually controlled.
- **Current_Day**: The Day_Cell whose date matches the date portion of the Tracked_Date.
- **Selected_Day**: The Day_Cell most recently clicked by the user.
- **Day_Detail_Sidebar**: The right-side panel that appears when a Day_Cell is clicked, showing details for the Selected_Day.
- **Month_Header**: The area at the top of the Calendar_View displaying the current month name and year, with navigation arrows.
- **Tracked_Date_Banner**: The bold banner displayed at the top of the Calendar_Tab showing the full Tracked_Date.
- **Close_Button**: The button (e.g., an 'X' button) displayed in the Day_Detail_Sidebar that, when clicked, hides the sidebar and deselects the Selected_Day.

---

## Requirements

### Requirement 1: Calendar Tab Integration

**User Story:** As a DM, I want a dedicated Calendar tab in the main window, so that I can access time-tracking tools without leaving the application.

#### Acceptance Criteria

1. THE Calendar_Tab SHALL be added as a tab in the main application tab widget, labelled "Calendar".
2. THE Calendar_Tab SHALL display the Calendar_View on the left side and the Day_Detail_Sidebar on the right side within a horizontal split layout.
3. WHEN the Calendar_Tab is first displayed, THE Calendar_View SHALL show the month containing the Tracked_Date.

---

### Requirement 2: Tracked Date Banner

**User Story:** As a DM, I want to see the current in-game date and time prominently displayed, so that I always know the in-game time reference at a glance.

#### Acceptance Criteria

1. THE Tracked_Date_Banner SHALL be displayed at the top of the Calendar_Tab, above the Calendar_View and Day_Detail_Sidebar.
2. THE Tracked_Date_Banner SHALL render the Tracked_Date in bold text showing the full date and time (e.g., "Monday, June 9, 2025 — 14:30").
3. THE Calendar_Tab SHALL initialise the Tracked_Date to the current real-world date at midnight (00:00) on first load.

---

### Requirement 3: Month View Display

**User Story:** As a DM, I want to see a monthly calendar grid, so that I can visualise the in-game month at a glance.

#### Acceptance Criteria

1. THE Calendar_View SHALL display a Month_Header containing the month name and four-digit year of the currently viewed month.
2. THE Calendar_View SHALL display a row of weekday labels in order: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday.
3. THE Calendar_View SHALL display Day_Cells arranged in a grid where each row represents one week, aligned to the Sunday–Saturday column order.
4. THE Calendar_View SHALL display only Day_Cells belonging to the currently viewed month; cells for days outside the current month SHALL be left empty.

---

### Requirement 4: Month Navigation

**User Story:** As a DM, I want to navigate between months, so that I can view past and future calendar months.

#### Acceptance Criteria

1. THE Month_Header SHALL contain a left arrow button and a right arrow button flanking the month name and year label.
2. WHEN the left arrow button is clicked, THE Calendar_View SHALL update to display the previous calendar month.
3. WHEN the right arrow button is clicked, THE Calendar_View SHALL update to display the next calendar month.
4. WHEN the displayed month changes, THE Calendar_View SHALL re-render all Day_Cells for the new month.

---

### Requirement 5: Day Visual States

**User Story:** As a DM, I want past days, the current in-game day, and future days to look visually distinct, so that I can orient myself in time at a glance.

#### Acceptance Criteria

1. THE Calendar_View SHALL render the Current_Day with a distinct highlight style (e.g., accent-coloured background) that differs from all other Day_Cells.
2. THE Calendar_View SHALL render Day_Cells whose date is earlier than the Tracked_Date with a visually muted style (e.g., greyed-out text and background).
3. THE Calendar_View SHALL render Day_Cells whose date is later than the Tracked_Date with the default (unmodified) style.
4. WHEN the Tracked_Date changes, THE Calendar_View SHALL update the visual state of all Day_Cells to reflect the new Tracked_Date.

---

### Requirement 6: Day Selection

**User Story:** As a DM, I want to click on a day to select it, so that I can view details about that specific day.

#### Acceptance Criteria

1. WHEN a Day_Cell is clicked, THE Calendar_Tab SHALL mark that Day_Cell as the Selected_Day.
2. THE Calendar_View SHALL render the Selected_Day with a distinct highlight style that differs from both the Current_Day highlight and the default Day_Cell style.
3. WHEN a different Day_Cell is clicked, THE Calendar_View SHALL remove the Selected_Day highlight from the previously selected Day_Cell and apply it to the newly clicked Day_Cell.
4. WHEN the displayed month changes, THE Calendar_View SHALL preserve the Selected_Day if it falls within the new month; otherwise THE Calendar_View SHALL deselect the Selected_Day.

---

### Requirement 7: Day Detail Sidebar

**User Story:** As a DM, I want a sidebar to appear when I click a day, so that I have a dedicated area for day-specific information.

#### Acceptance Criteria

1. WHEN a Day_Cell is clicked, THE Day_Detail_Sidebar SHALL become visible and display the date of the Selected_Day as a header.
2. WHEN no Day_Cell is selected, THE Day_Detail_Sidebar SHALL be hidden.
3. THE Day_Detail_Sidebar SHALL display a placeholder message indicating that detailed day content will be available in a future update.
4. WHEN a different Day_Cell is clicked, THE Day_Detail_Sidebar SHALL update its header to reflect the newly Selected_Day's date.
5. THE Day_Detail_Sidebar SHALL display a Close_Button that, when clicked, hides the Day_Detail_Sidebar and deselects the Selected_Day.
6. WHEN the Selected_Day's Day_Cell is single left-clicked again, THE Day_Detail_Sidebar SHALL be hidden and the Selected_Day SHALL be deselected.
