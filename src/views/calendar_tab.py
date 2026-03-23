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
    QSplitter,
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

        self.setFixedSize(52, 52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
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

    def __init__(self, year: int, month: int, parent=None) -> None:
        super().__init__(parent)
        self._year = year
        self._month = month
        self._cells: list[DayCell] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

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
        root.addLayout(header_layout)

        # Grid container
        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(2)
        root.addWidget(self._grid_widget)
        root.addStretch()

        self._rebuild_grid()

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

        # Tracked date banner
        self._banner = QLabel(self._format_tracked_date())
        self._banner.setStyleSheet("font-weight: bold; font-size: 15px;")
        root.addWidget(self._banner)

        # Splitter: CalendarView (left) + DayDetailSidebar (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._calendar_view = CalendarView(
            self._tracked_date.year, self._tracked_date.month
        )
        self._sidebar = DayDetailSidebar()

        splitter.addWidget(self._calendar_view)
        splitter.addWidget(self._sidebar)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)

        # Connect signals
        for cell in self._calendar_view._cells:
            cell.clicked.connect(self._on_day_clicked)

        self._calendar_view.month_changed.connect(self._on_month_changed)
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

    def _format_tracked_date(self) -> str:
        return _format_date(self._tracked_date.date()) + " — " + self._tracked_date.strftime("%H:%M")
