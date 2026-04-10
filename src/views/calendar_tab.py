import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer

from src.models import CalendarDefinition, FantasyDateTime, IntercalaryPeriod, GREGORIAN_DEFAULT, Project, Project


# ---------------------------------------------------------------------------
# Simple date-like container for calendar cells
# ---------------------------------------------------------------------------

class _CalDate:
    """Lightweight year/month/day container used by DayCell."""
    __slots__ = ("year", "month", "day")

    def __init__(self, year: int, month: int, day: int) -> None:
        self.year = year
        self.month = month
        self.day = day

    def __eq__(self, other) -> bool:
        if isinstance(other, _CalDate):
            return self.year == other.year and self.month == other.month and self.day == other.day
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.year, self.month, self.day))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_date(date) -> str:
    """Format a _CalDate as 'Day N, Month Name, Year'."""
    return f"Day {date.day}, Month {date.month}, {date.year}"


# ---------------------------------------------------------------------------
# DayCell
# ---------------------------------------------------------------------------

_STATE_STYLES = {
    "past": "background-color: #2a2a2a; color: #666666; border: 1px solid #3a3a3a;",
    "current": "background-color: #4CAF50; color: #ffffff; border: 1px solid #388E3C;",
    "future": "background-color: transparent; color: palette(text); border: 1px solid #555555;",
    "selected": "background-color: #6EC6FF; color: #000000; border: 1px solid #1E88E5;",
}


class DayCell(QFrame):
    clicked = pyqtSignal(object)  # carries _CalDate

    def __init__(self, date: _CalDate, parent=None) -> None:
        super().__init__(parent)
        self._date = date
        self._state = "future"

        self.setFixedSize(40, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(str(date.day))
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        self.set_state("future")

    @property
    def date(self) -> _CalDate:
        return self._date

    def set_state(self, state: str) -> None:
        self._state = state
        style = _STATE_STYLES.get(state, _STATE_STYLES["future"])
        self.setStyleSheet(f"DayCell {{ {style} }}")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._date)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# CalendarView
# ---------------------------------------------------------------------------

class CalendarView(QWidget):
    month_changed = pyqtSignal()
    # Signal carries delta in seconds (positive = forward, negative = backward)
    time_adjusted = pyqtSignal(int)
    # Signal carries delta in years (positive = forward, negative = backward)
    year_adjusted = pyqtSignal(int)

    def __init__(self, calendar_def: CalendarDefinition, year: int, month: int, parent=None) -> None:
        super().__init__(parent)
        self._calendar_def = calendar_def
        self._year = year
        self._month = month
        # When not None, we are viewing this intercalary period instead of a regular month
        self._intercalary_period: IntercalaryPeriod | None = None
        self._intercalary_period_idx: int | None = None  # index into calendar.intercalary_periods
        self._cells: list[DayCell] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Tracked date banner with time adjustment buttons — spans full width
        _increments = [
            (10,    "10s"),
            (60,    "1m"),
            (600,   "10m"),
            (3600,  "1h"),
            (28800, "8h"),
            (86400, "1d"),
        ]

        banner_row = QHBoxLayout()
        banner_row.setSpacing(2)

        # Left side: largest → smallest (smallest closest to the date label)
        # Order: −1y, −1d, −8h, −1h, −10m, −1m, −10s
        prev_year_btn = QPushButton("−1y")
        prev_year_btn.setFixedHeight(22)
        prev_year_btn.setStyleSheet("font-size: 10px; padding: 0 4px;")
        prev_year_btn.clicked.connect(lambda: self.year_adjusted.emit(-1))
        banner_row.addWidget(prev_year_btn)

        for seconds, label in reversed(_increments):
            btn = QPushButton(f"−{label}")
            btn.setFixedHeight(22)
            btn.setStyleSheet("font-size: 10px; padding: 0 4px;")
            btn.clicked.connect(lambda _, s=seconds: self.time_adjusted.emit(-s))
            banner_row.addWidget(btn)

        self._banner = QLabel()
        self._banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._banner.setStyleSheet("font-weight: bold; font-size: 15px; padding: 0 6px;")

        # Fix the banner width to the longest possible date string (5-digit year, longest month/weekday names)
        from PyQt6.QtGui import QFontMetrics, QFont
        banner_font = QFont()
        banner_font.setBold(True)
        banner_font.setPointSize(15)
        fm = QFontMetrics(banner_font)
        longest_month = max((m.name for m in calendar_def.months), key=len) if calendar_def.months else "September"
        longest_weekday = max(calendar_def.weekday_names, key=len) if calendar_def.weekday_names else "Wednesday"
        longest_era = max((e.name for e in calendar_def.eras), key=len) if calendar_def.eras else ""
        era_suffix = f" {longest_era}" if longest_era else ""
        sample = f"{longest_weekday}, {longest_month} 99, 99999{era_suffix} — 99:99"
        self._banner.setMinimumWidth(fm.horizontalAdvance(sample) + 20)

        banner_row.addWidget(self._banner)

        # Right side: +10s +1m +10m +1h +8h +1d +1y
        for seconds, label in _increments:
            btn = QPushButton(f"+{label}")
            btn.setFixedHeight(22)
            btn.setStyleSheet("font-size: 10px; padding: 0 4px;")
            btn.clicked.connect(lambda _, s=seconds: self.time_adjusted.emit(s))
            banner_row.addWidget(btn)

        next_year_btn = QPushButton("+1y")
        next_year_btn.setFixedHeight(22)
        next_year_btn.setStyleSheet("font-size: 10px; padding: 0 4px;")
        next_year_btn.clicked.connect(lambda: self.year_adjusted.emit(1))
        banner_row.addWidget(next_year_btn)

        root.addLayout(banner_row)

        # Inner container — Fixed size so the grid columns don't stretch
        self._inner = QWidget()
        self._inner.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        inner_layout = QVBoxLayout(self._inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(4)

        # Month header
        header_layout = QHBoxLayout()
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedWidth(32)
        self._prev_btn.clicked.connect(self._go_prev_month)

        self._month_label = QLabel()
        self._month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedWidth(32)
        self._next_btn.clicked.connect(self._go_next_month)

        header_layout.addWidget(self._prev_btn)
        header_layout.addWidget(self._month_label, stretch=1)
        header_layout.addWidget(self._next_btn)
        inner_layout.addLayout(header_layout)

        # Grid container
        self._grid_widget = QWidget()
        self._grid_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(0)
        self._grid.setContentsMargins(0, 0, 0, 0)
        inner_layout.addWidget(self._grid_widget)

        root.addWidget(self._inner, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self._rebuild_grid()

    def set_banner_text(self, text: str) -> None:
        self._banner.setText(text)

    # ------------------------------------------------------------------
    # Navigation sequence helpers
    # ------------------------------------------------------------------

    def _nav_sequence(self) -> list:
        """Return ordered list of navigation slots for the current year.

        Each slot is either:
          ('month', month_1based)
          ('intercalary', IntercalaryPeriod, after_month_0based, ip_index)
        """
        seq = []
        for i, _ in enumerate(self._calendar_def.months):
            seq.append(('month', i + 1))
            for ip_idx, ip in enumerate(self._calendar_def.intercalary_periods):
                if ip.after_month == i:
                    seq.append(('intercalary', ip, i, ip_idx))
        return seq

    def _current_slot_index(self) -> int:
        seq = self._nav_sequence()
        if self._intercalary_period is None:
            for idx, slot in enumerate(seq):
                if slot[0] == 'month' and slot[1] == self._month:
                    return idx
        else:
            for idx, slot in enumerate(seq):
                if slot[0] == 'intercalary' and slot[1] is self._intercalary_period:
                    return idx
        return 0

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _go_prev_month(self) -> None:
        seq = self._nav_sequence()
        idx = self._current_slot_index()
        if idx == 0:
            self._year -= 1
            self._month = len(self._calendar_def.months)
            self._intercalary_period = None
            self._intercalary_period_idx = None
            prev_seq = self._nav_sequence()
            last = prev_seq[-1]
            if last[0] == 'intercalary':
                self._intercalary_period = last[1]
                self._intercalary_period_idx = last[3]
                self._month = last[2] + 1
        else:
            prev_slot = seq[idx - 1]
            if prev_slot[0] == 'month':
                self._month = prev_slot[1]
                self._intercalary_period = None
                self._intercalary_period_idx = None
            else:
                self._intercalary_period = prev_slot[1]
                self._intercalary_period_idx = prev_slot[3]
                self._month = prev_slot[2] + 1
        self._rebuild_grid()
        self.month_changed.emit()

    def _go_next_month(self) -> None:
        seq = self._nav_sequence()
        idx = self._current_slot_index()
        if idx == len(seq) - 1:
            self._year += 1
            self._month = 1
            self._intercalary_period = None
            self._intercalary_period_idx = None
        else:
            next_slot = seq[idx + 1]
            if next_slot[0] == 'month':
                self._month = next_slot[1]
                self._intercalary_period = None
                self._intercalary_period_idx = None
            else:
                self._intercalary_period = next_slot[1]
                self._intercalary_period_idx = next_slot[3]
                self._month = next_slot[2] + 1
        self._rebuild_grid()
        self.month_changed.emit()

    # ------------------------------------------------------------------
    # Grid construction
    # ------------------------------------------------------------------

    def _rebuild_grid(self) -> None:
        # Clear existing grid items
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._cells.clear()

        if self._intercalary_period is not None:
            self._rebuild_grid_intercalary()
        else:
            self._rebuild_grid_month()

    def _rebuild_grid_month(self) -> None:
        # Clamp month to valid range in case of stale state after calendar switch
        self._month = max(1, min(self._month, len(self._calendar_def.months)))
        month_def = self._calendar_def.months[self._month - 1]
        self._month_label.setText(month_def.name + " " + str(self._year))

        week_length = self._calendar_def.week_length
        for col, name in enumerate(self._calendar_def.weekday_names):
            lbl = QLabel(name[:3])
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: palette(text);")
            self._grid.addWidget(lbl, 0, col)

        first_day = FantasyDateTime(
            calendar=self._calendar_def,
            year=self._year,
            month=self._month,
            day=1,
            hour=0,
            minute=0,
            second=0,
        )
        start_col = first_day.day_of_week()

        day_count = month_def.effective_day_count(self._year)
        for day_num in range(1, day_count + 1):
            col = (start_col + day_num - 1) % week_length
            row = (start_col + day_num - 1) // week_length + 1
            date = _CalDate(self._year, self._month, day_num)
            cell = DayCell(date)
            self._cells.append(cell)
            self._grid.addWidget(cell, row, col)

    def _rebuild_grid_intercalary(self) -> None:
        ip = self._intercalary_period
        self._month_label.setText(f"{ip.name} {self._year}")

        week_length = self._calendar_def.week_length
        # No weekday headers for intercalary periods — just lay days out left-to-right
        for day_num in range(1, ip.day_count + 1):
            col = (day_num - 1) % week_length
            row = (day_num - 1) // week_length
            # Use month=0 as sentinel so refresh_states treats these as intercalary
            date = _CalDate(self._year, 0, day_num)
            cell = DayCell(date)
            self._cells.append(cell)
            self._grid.addWidget(cell, row, col)

    def set_calendar(self, cal: CalendarDefinition) -> None:
        self._calendar_def = cal
        self._intercalary_period = None
        self._intercalary_period_idx = None
        self._month = 1
        self._update_banner_width()
        self._rebuild_grid()

    def _update_banner_width(self) -> None:
        from PyQt6.QtGui import QFontMetrics, QFont
        banner_font = QFont()
        banner_font.setBold(True)
        banner_font.setPointSize(15)
        fm = QFontMetrics(banner_font)
        cal = self._calendar_def
        longest_month = max((m.name for m in cal.months), key=len) if cal.months else "September"
        longest_weekday = max(cal.weekday_names, key=len) if cal.weekday_names else "Wednesday"
        longest_era = max((e.name for e in cal.eras), key=len) if cal.eras else ""
        era_suffix = f" {longest_era}" if longest_era else ""
        sample = f"{longest_weekday}, {longest_month} 99, 99999{era_suffix} — 99:99"
        self._banner.setMinimumWidth(fm.horizontalAdvance(sample) + 20)

    # ------------------------------------------------------------------
    # State refresh
    # ------------------------------------------------------------------

    def refresh_states(self, tracked_date: FantasyDateTime, selected_date) -> None:
        tracked_abs = tracked_date.total_elapsed_days()
        for cell in self._cells:
            cd = cell.date
            if selected_date is not None and cd == selected_date:
                cell.set_state("selected")
            elif cd.month == 0:
                # Intercalary cell — build a FantasyDateTime to get its absolute day
                if self._intercalary_period_idx is None:
                    cell.set_state("future")
                    continue
                cell_fdt = FantasyDateTime(
                    calendar=self._calendar_def,
                    year=self._year,
                    month=self._calendar_def.intercalary_periods[self._intercalary_period_idx].after_month + 1,
                    day=cd.day,
                    hour=0, minute=0, second=0,
                    intercalary_period_index=self._intercalary_period_idx,
                )
                cell_abs = cell_fdt.total_elapsed_days()
                if cell_abs == tracked_abs:
                    cell.set_state("current")
                elif cell_abs < tracked_abs:
                    cell.set_state("past")
                else:
                    cell.set_state("future")
            elif cd.year == tracked_date.year and cd.month == tracked_date.month and cd.day == tracked_date.day and not tracked_date.is_intercalary:
                cell.set_state("current")
            elif (cd.year, cd.month, cd.day) < (tracked_date.year, tracked_date.month, tracked_date.day):
                cell.set_state("past")
            else:
                cell.set_state("future")

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def year(self) -> int:
        return self._year

    @property
    def month(self) -> int:
        return self._month

    @property
    def intercalary_period(self) -> IntercalaryPeriod | None:
        return self._intercalary_period


# ---------------------------------------------------------------------------
# DayDetailSidebar
# ---------------------------------------------------------------------------

class DayDetailSidebar(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header row: date label + close button
        header_row = QHBoxLayout()
        self._date_label = QLabel()
        self._date_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_row.addWidget(self._date_label, stretch=1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.close_requested)
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        placeholder = QLabel("Detailed day content will be available in a future update.")
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("color: palette(mid);")
        layout.addWidget(placeholder)

        # Lunar phases container
        self._lunar_widget = QWidget()
        self._lunar_container = QVBoxLayout(self._lunar_widget)
        self._lunar_container.setContentsMargins(0, 4, 0, 0)
        self._lunar_container.setSpacing(2)
        self._lunar_widget.hide()
        layout.addWidget(self._lunar_widget)

        layout.addStretch()

        self.hide()

    def show_day(self, date: _CalDate) -> None:
        self._date_label.setText(_format_date(date))
        self.show()

    def show_lunar_phases(self, fdt: FantasyDateTime, cal: CalendarDefinition) -> None:
        # Clear existing widgets from the lunar container
        while self._lunar_container.count():
            item = self._lunar_container.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        if cal.lunar_cycles:
            for cycle in cal.lunar_cycles:
                label = QLabel(f"{cycle.name}: {fdt.lunar_phase(cycle)}")
                self._lunar_container.addWidget(label)
            self._lunar_widget.show()
        else:
            self._lunar_widget.hide()

    def hide_sidebar(self) -> None:
        self.hide()


# ---------------------------------------------------------------------------
# CalendarTab
# ---------------------------------------------------------------------------

class CalendarTab(QWidget):
    calendar_selection_cancelled = pyqtSignal()  # emitted when user cancels the calendar selector
    def __init__(self, calendar_def: CalendarDefinition | None = None, parent=None) -> None:
        super().__init__(parent)

        self._calendar_def = calendar_def if calendar_def is not None else GREGORIAN_DEFAULT
        self._calendar_selection_pending = False  # True when project has no calendar chosen yet

        today = datetime.date.today()
        self._tracked_date = FantasyDateTime(
            calendar=self._calendar_def,
            year=today.year,
            month=today.month,
            day=today.day,
            hour=0,
            minute=0,
            second=0,
        )
        self._selected_date: _CalDate | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        # Vertical layout: CalendarView on top, DayDetailSidebar below
        self._calendar_view = CalendarView(
            self._calendar_def, self._tracked_date.year, self._tracked_date.month
        )
        self._calendar_view.set_banner_text(self._format_tracked_date())

        self._sidebar = DayDetailSidebar()
        self._sidebar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        root.addWidget(self._calendar_view, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        root.addWidget(self._sidebar)

        # Connect signals
        for cell in self._calendar_view._cells:
            cell.clicked.connect(self._on_day_clicked)

        self._calendar_view.month_changed.connect(self._on_month_changed)
        self._calendar_view.time_adjusted.connect(self._on_time_adjusted)
        self._calendar_view.year_adjusted.connect(self._on_year_adjusted)
        self._sidebar.close_requested.connect(self._on_close_requested)

        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._calendar_selection_pending:
            self._calendar_selection_pending = False
            QTimer.singleShot(0, self._prompt_calendar_selection)

    def _prompt_calendar_selection(self) -> None:
        from src.views.calendar_selector_dialog import CalendarSelectorDialog
        dialog = CalendarSelectorDialog(self.window())
        if dialog.exec() == CalendarSelectorDialog.DialogCode.Accepted:
            calendar = dialog.get_calendar()
            if calendar is not None:
                self._calendar_def = calendar
                self._calendar_view.set_calendar(calendar)
                # Use the calendar's initial date if provided, otherwise fall back to year 1 month 1 day 1
                initial_date = dialog.get_initial_date()
                if initial_date is not None:
                    self._tracked_date = initial_date
                else:
                    self._tracked_date = FantasyDateTime(
                        calendar=self._calendar_def,
                        year=1,
                        month=1,
                        day=1,
                        hour=0,
                        minute=0,
                        second=0,
                    )
                td = self._tracked_date
                cv = self._calendar_view
                cv._year = td.year
                if td.is_intercalary:
                    ip = td.calendar.intercalary_periods[td.intercalary_period_index]
                    cv._month = ip.after_month + 1
                    cv._intercalary_period = ip
                    cv._intercalary_period_idx = td.intercalary_period_index
                else:
                    cv._month = td.month
                    cv._intercalary_period = None
                    cv._intercalary_period_idx = None
                cv._rebuild_grid()
                for cell in cv._cells:
                    cell.clicked.connect(self._on_day_clicked)
                self._calendar_view.set_banner_text(self._format_tracked_date())
                self._calendar_view.show()
                self._calendar_view.refresh_states(self._tracked_date, self._selected_date)
        else:
            self.calendar_selection_cancelled.emit()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_day_clicked(self, date: _CalDate) -> None:
        if self._selected_date == date:
            self._selected_date = None
            self._sidebar.hide_sidebar()
        else:
            self._selected_date = date
            self._sidebar.show_day(date)
            if date.month == 0:
                # Intercalary cell — construct FantasyDateTime with the period index
                ip_idx = self._calendar_view._intercalary_period_idx
                if ip_idx is not None:
                    fdt = FantasyDateTime(
                        calendar=self._calendar_def,
                        year=date.year,
                        month=self._calendar_def.intercalary_periods[ip_idx].after_month + 1,
                        day=date.day,
                        hour=0,
                        minute=0,
                        second=0,
                        intercalary_period_index=ip_idx,
                    )
                    self._sidebar.show_lunar_phases(fdt, self._calendar_def)
            else:
                fdt = FantasyDateTime(
                    calendar=self._calendar_def,
                    year=date.year,
                    month=date.month,
                    day=date.day,
                    hour=0,
                    minute=0,
                    second=0,
                )
                self._sidebar.show_lunar_phases(fdt, self._calendar_def)
        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    def _on_time_adjusted(self, delta_seconds: int) -> None:
        self._tracked_date = self._tracked_date.add_seconds(delta_seconds)
        self._calendar_view.set_banner_text(self._format_tracked_date())

        td = self._tracked_date
        cv = self._calendar_view

        # Determine if the view needs to change to follow the tracked date
        if td.is_intercalary:
            if (cv.intercalary_period is None
                    or cv._intercalary_period_idx != td.intercalary_period_index
                    or cv.year != td.year):
                ip = td.calendar.intercalary_periods[td.intercalary_period_index]
                cv._year = td.year
                cv._month = ip.after_month + 1
                cv._intercalary_period = ip
                cv._intercalary_period_idx = td.intercalary_period_index
                cv._rebuild_grid()
                for cell in cv._cells:
                    cell.clicked.connect(self._on_day_clicked)
        else:
            if (cv.intercalary_period is not None
                    or cv.year != td.year
                    or cv.month != td.month):
                cv._year = td.year
                cv._month = td.month
                cv._intercalary_period = None
                cv._intercalary_period_idx = None
                cv._rebuild_grid()
                for cell in cv._cells:
                    cell.clicked.connect(self._on_day_clicked)

        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    def _on_year_adjusted(self, delta_years: int) -> None:
        td = self._tracked_date
        new_year = td.year + delta_years
        if new_year < 1:
            new_year = 1
        # Clamp day to the new year's month day count (handles leap year edge cases)
        if not td.is_intercalary:
            max_day = td.calendar.months[td.month - 1].effective_day_count(new_year)
            new_day = min(td.day, max_day)
            self._tracked_date = FantasyDateTime(
                calendar=td.calendar,
                year=new_year,
                month=td.month,
                day=new_day,
                hour=td.hour,
                minute=td.minute,
                second=td.second,
                era=td.era,
            )
        else:
            ip = td.calendar.intercalary_periods[td.intercalary_period_index]
            self._tracked_date = FantasyDateTime(
                calendar=td.calendar,
                year=new_year,
                month=td.month,
                day=td.day,
                hour=td.hour,
                minute=td.minute,
                second=td.second,
                era=td.era,
                intercalary_period_index=td.intercalary_period_index,
            )
        cv = self._calendar_view
        cv._year = self._tracked_date.year
        cv._intercalary_period = None
        cv._intercalary_period_idx = None
        cv._month = self._tracked_date.month
        cv._rebuild_grid()
        for cell in cv._cells:
            cell.clicked.connect(self._on_day_clicked)
        self._calendar_view.set_banner_text(self._format_tracked_date())
        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    def _on_close_requested(self) -> None:
        self._selected_date = None
        self._sidebar.hide_sidebar()
        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    def _on_month_changed(self) -> None:
        # Clear selection if selected date is not in the current view slot
        if self._selected_date is not None:
            cv = self._calendar_view
            if cv.intercalary_period is not None:
                # Viewing an intercalary period — clear any regular-month selection
                if self._selected_date.month != 0:
                    self._selected_date = None
                    self._sidebar.hide_sidebar()
            else:
                if (
                    self._selected_date.year != cv.year
                    or self._selected_date.month != cv.month
                ):
                    self._selected_date = None
                    self._sidebar.hide_sidebar()
        # Re-connect clicked signals for newly created cells
        for cell in self._calendar_view._cells:
            cell.clicked.connect(self._on_day_clicked)

        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    # ------------------------------------------------------------------
    # Project integration
    # ------------------------------------------------------------------

    def load_from_project(self, project: Project) -> None:
        self._calendar_def = project.calendar_definition
        self._calendar_view.set_calendar(self._calendar_def)

        # If calendar_source is empty, this is a new project — prompt on first tab visit
        self._calendar_selection_pending = not project.calendar_source

        if project.tracked_date is not None:
            self._tracked_date = project.tracked_date
        else:
            today = datetime.date.today()
            self._tracked_date = FantasyDateTime(
                calendar=self._calendar_def,
                year=today.year,
                month=today.month,
                day=today.day,
                hour=0,
                minute=0,
                second=0,
            )

        td = self._tracked_date
        cv = self._calendar_view
        cv._year = td.year
        if td.is_intercalary:
            ip = td.calendar.intercalary_periods[td.intercalary_period_index]
            cv._month = ip.after_month + 1
            cv._intercalary_period = ip
            cv._intercalary_period_idx = td.intercalary_period_index
        else:
            cv._month = td.month
            cv._intercalary_period = None
            cv._intercalary_period_idx = None
        cv._rebuild_grid()
        for cell in cv._cells:
            cell.clicked.connect(self._on_day_clicked)

        self._calendar_view.set_banner_text(self._format_tracked_date())

        if self._calendar_selection_pending:
            self._calendar_view.hide()
        else:
            self._calendar_view.show()
            self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    def flush_to_project(self, project: Project) -> None:
        project.tracked_date = self._tracked_date
        project.calendar_definition = self._calendar_def
        if not project.calendar_source:
            project.calendar_source = self._calendar_def.name

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def advance_time(self, seconds: int) -> None:
        """Advance (or rewind) the tracked date by the given number of seconds."""
        self._on_time_adjusted(seconds)

    def _format_tracked_date(self) -> str:
        fdt = self._tracked_date
        cal = fdt.calendar
        # Always resolve era dynamically from the absolute year.
        # Sort by absolute_start so earlier-starting eras are checked first,
        # giving correct results even if eras are defined out of order.
        active_era = next(
            (e for e in sorted(cal.eras, key=lambda e: e.absolute_start)
             if e.contains_year(fdt.year)),
            None
        )
        if active_era is not None:
            display_yr = active_era.display_year(fdt.year)
            era_str = f" {active_era.name}"
        else:
            display_yr = fdt.year
            era_str = ""
        if fdt.is_intercalary:
            ip = cal.intercalary_periods[fdt.intercalary_period_index]
            return f"{ip.name}, Day {fdt.day}, {display_yr}{era_str} — {fdt.hour:02d}:{fdt.minute:02d}"
        month_name = cal.months[fdt.month - 1].name
        weekday_name = cal.weekday_names[fdt.day_of_week()]
        return f"{weekday_name}, {month_name} {fdt.day}, {display_yr}{era_str} — {fdt.hour:02d}:{fdt.minute:02d}"
