import datetime
import calendar

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
from PyQt6.QtCore import pyqtSignal, Qt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_date(date: datetime.date) -> str:
    """Format a date as 'Monday, June 9, 2025' (no zero-padded day, cross-platform)."""
    return date.strftime("%A, %B") + f" {date.day}, " + date.strftime("%Y")


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
    clicked = pyqtSignal(object)  # carries datetime.date

    def __init__(self, date: datetime.date, parent=None) -> None:
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
    def date(self) -> datetime.date:
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

    def __init__(self, year: int, month: int, parent=None) -> None:
        super().__init__(parent)
        self._year = year
        self._month = month
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
        for seconds, label in reversed(_increments):
            btn = QPushButton(f"−{label}")
            btn.setFixedHeight(22)
            btn.setStyleSheet("font-size: 10px; padding: 0 4px;")
            btn.clicked.connect(lambda _, s=seconds: self.time_adjusted.emit(-s))
            banner_row.addWidget(btn)

        self._banner = QLabel()
        self._banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._banner.setStyleSheet("font-weight: bold; font-size: 15px; padding: 0 6px;")
        banner_row.addWidget(self._banner, stretch=1)

        # Right side: smallest → largest
        for seconds, label in _increments:
            btn = QPushButton(f"+{label}")
            btn.setFixedHeight(22)
            btn.setStyleSheet("font-size: 10px; padding: 0 4px;")
            btn.clicked.connect(lambda _, s=seconds: self.time_adjusted.emit(s))
            banner_row.addWidget(btn)

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
    # Navigation
    # ------------------------------------------------------------------

    def _go_prev_month(self) -> None:
        if self._month == 1:
            self._month = 12
            self._year -= 1
        else:
            self._month -= 1
        self._rebuild_grid()
        self.month_changed.emit()

    def _go_next_month(self) -> None:
        if self._month == 12:
            self._month = 1
            self._year += 1
        else:
            self._month += 1
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
                w.setParent(None)
                w.deleteLater()
        self._cells.clear()

        # Update month label
        month_name = datetime.date(self._year, self._month, 1).strftime("%B %Y")
        self._month_label.setText(month_name)

        # Weekday headers (Sunday=0 … Saturday=6)
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for col, name in enumerate(day_names):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: palette(text);")
            self._grid.addWidget(lbl, 0, col)

        # calendar.monthcalendar returns weeks as lists of 7 ints (Mon=0…Sun=6), 0 = no day
        # We need Sunday-first ordering, so we use calendar.Calendar(firstweekday=6)
        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdayscalendar(self._year, self._month)

        for row_idx, week in enumerate(weeks):
            for col_idx, day_num in enumerate(week):
                if day_num == 0:
                    continue
                date = datetime.date(self._year, self._month, day_num)
                cell = DayCell(date)
                self._cells.append(cell)
                self._grid.addWidget(cell, row_idx + 1, col_idx)

    # ------------------------------------------------------------------
    # State refresh
    # ------------------------------------------------------------------

    def refresh_states(self, tracked_date: datetime.datetime, selected_date) -> None:
        today = tracked_date.date()
        for cell in self._cells:
            if selected_date is not None and cell.date == selected_date:
                cell.set_state("selected")
            elif cell.date == today:
                cell.set_state("current")
            elif cell.date < today:
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
        layout.addStretch()

        self.hide()

    def show_day(self, date: datetime.date) -> None:
        self._date_label.setText(_format_date(date))
        self.show()

    def hide_sidebar(self) -> None:
        self.hide()


# ---------------------------------------------------------------------------
# CalendarTab
# ---------------------------------------------------------------------------

class CalendarTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._tracked_date = datetime.datetime.combine(
            datetime.date.today(), datetime.time(0, 0)
        )
        self._selected_date: datetime.date | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        # Vertical layout: CalendarView on top, DayDetailSidebar below
        self._calendar_view = CalendarView(
            self._tracked_date.year, self._tracked_date.month
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
        self._sidebar.close_requested.connect(self._on_close_requested)

        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_day_clicked(self, date: datetime.date) -> None:
        if self._selected_date == date:
            self._selected_date = None
            self._sidebar.hide_sidebar()
        else:
            self._selected_date = date
            self._sidebar.show_day(date)
        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    def _on_time_adjusted(self, delta_seconds: int) -> None:
        self._tracked_date += datetime.timedelta(seconds=delta_seconds)
        self._calendar_view.set_banner_text(self._format_tracked_date())
        # If the tracked date moved to a different month, navigate the view there
        if (self._tracked_date.year != self._calendar_view.year or
                self._tracked_date.month != self._calendar_view.month):
            self._calendar_view._year = self._tracked_date.year
            self._calendar_view._month = self._tracked_date.month
            self._calendar_view._rebuild_grid()
            for cell in self._calendar_view._cells:
                cell.clicked.connect(self._on_day_clicked)
        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    def _on_close_requested(self) -> None:
        self._selected_date = None
        self._sidebar.hide_sidebar()
        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    def _on_month_changed(self) -> None:
        # Clear selection if selected date is not in the new month
        if self._selected_date is not None:
            if (
                self._selected_date.year != self._calendar_view.year
                or self._selected_date.month != self._calendar_view.month
            ):
                self._selected_date = None
                self._sidebar.hide_sidebar()

        # Re-connect clicked signals for newly created cells
        for cell in self._calendar_view._cells:
            cell.clicked.connect(self._on_day_clicked)

        self._calendar_view.refresh_states(self._tracked_date, self._selected_date)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def advance_time(self, seconds: int) -> None:
        """Advance (or rewind) the tracked date by the given number of seconds."""
        self._on_time_adjusted(seconds)

    def _format_tracked_date(self) -> str:
        return _format_date(self._tracked_date.date()) + " — " + self._tracked_date.strftime("%H:%M")
