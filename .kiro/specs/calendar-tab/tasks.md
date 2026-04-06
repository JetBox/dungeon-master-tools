# Implementation Plan: Calendar Tab

## Overview

Add a Calendar tab to the main window using PyQt6. The tab displays a monthly grid of days with visual states for past/present/future, a tracked date banner, month navigation, day selection, and a collapsible day detail sidebar.

## Tasks

- [x] 1. Add CalendarDay data model to `src/models.py`
  - Add a `CalendarDay` dataclass with `date: datetime.date` field
  - _Requirements: 2.3, 5.1, 5.2, 5.3_

- [x] 2. Implement `DayCell` widget in `src/views/calendar_tab.py`
  - [x] 2.1 Create `DayCell(QFrame)` with a day number label
    - Accept a `datetime.date` and emit a `clicked` signal carrying the date
    - Apply stylesheet based on visual state: past (muted), current (accent), future (default), selected (distinct highlight)
    - _Requirements: 5.1, 5.2, 5.3, 6.1, 6.2_
  - [x] 2.2 Add `set_state(state: str)` method to `DayCell`
    - States: `"past"`, `"current"`, `"future"`, `"selected"`
    - _Requirements: 5.1, 5.2, 5.3, 6.2_

- [x] 3. Implement `CalendarView` widget in `src/views/calendar_tab.py`
  - [x] 3.1 Build the month grid layout
    - `QGridLayout` with a weekday header row (Sun–Sat) and day cell rows
    - Only populate cells for days in the current viewed month; leave others empty
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 3.2 Add `Month_Header` with left/right arrow buttons and month+year label
    - Connect arrows to `_go_prev_month` / `_go_next_month` slots that re-render the grid
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 3.3 Add `refresh_states(tracked_date, selected_date)` method
    - Iterates all `DayCell`s and calls `set_state` based on comparison to `tracked_date`
    - Applies selected highlight to the matching cell if `selected_date` is in the viewed month
    - _Requirements: 5.4, 6.3, 6.4_

- [x] 4. Implement `DayDetailSidebar` widget in `src/views/calendar_tab.py`
  - [x] 4.1 Create `DayDetailSidebar(QWidget)` with a date header label, placeholder text, and a Close button
    - Hidden by default
    - Close button emits a `close_requested` signal
    - _Requirements: 7.1, 7.2, 7.3, 7.5_
  - [x] 4.2 Add `show_day(date: datetime.date)` and `hide_sidebar()` methods
    - `show_day` updates the header label and makes the widget visible
    - `hide_sidebar` hides the widget
    - _Requirements: 7.1, 7.2, 7.4_

- [x] 5. Implement `CalendarTab` and wire everything together in `src/views/calendar_tab.py`
  - [x] 5.1 Create `CalendarTab(QWidget)` with a vertical layout containing the `Tracked_Date_Banner` and a horizontal splitter holding `CalendarView` and `DayDetailSidebar`
    - Initialise `_tracked_date` to `datetime.date.today()` at midnight (00:00)
    - Render the `Tracked_Date_Banner` as bold text: e.g. "Monday, June 9, 2025 — 00:00"
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_
  - [x] 5.2 Connect `DayCell.clicked` → selection logic
    - On click: if the cell is already selected, deselect and hide sidebar; otherwise select it and call `sidebar.show_day(date)`
    - Update `CalendarView.refresh_states` after each selection change
    - _Requirements: 6.1, 6.3, 7.1, 7.6_
  - [x] 5.3 Connect `DayDetailSidebar.close_requested` → deselect and hide sidebar
    - _Requirements: 7.5_
  - [x] 5.4 Preserve or clear selection on month navigation
    - After month change, keep `_selected_date` if it falls in the new month; otherwise set to `None` and hide sidebar
    - _Requirements: 6.4_

- [x] 6. Register `CalendarTab` in `src/views/main_window.py`
  - Import `CalendarTab` and add it to `_tab_widget` with label `"Calendar"`
  - _Requirements: 1.1_

- [x] 7. Final checkpoint
  - Ensure all components are wired correctly, the tab appears in the main window, and navigation/selection/sidebar interactions work end-to-end. Ask the user if questions arise.
