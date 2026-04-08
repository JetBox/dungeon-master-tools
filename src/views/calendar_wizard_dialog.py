"""Multi-step wizard dialog for creating a custom CalendarDefinition."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.models import (
    CalendarDefinition,
    Era,
    EraDirection,
    FantasyDateTime,
    IntercalaryPeriod,
    LunarCycle,
    MonthDefinition,
)


# ---------------------------------------------------------------------------
# Base page interface
# ---------------------------------------------------------------------------

class _WizardPage(QWidget):
    """Base class for all wizard pages."""

    changed = pyqtSignal()  # emitted whenever any input changes

    def validate(self) -> str | None:
        """Return an error string, or None if the page is valid."""
        return None

    def collect(self) -> dict:
        """Return a dict of this page's data for final assembly."""
        return {}


# ---------------------------------------------------------------------------
# Delegates for QTableWidget inline editing
# ---------------------------------------------------------------------------

class _LineEditDelegate(QStyledItemDelegate):
    """Delegate that provides a QLineEdit editor for a table cell."""

    def createEditor(self, parent, option, index: QModelIndex):
        editor = QLineEdit(parent)
        return editor

    def setEditorData(self, editor: QLineEdit, index: QModelIndex):
        editor.setText(index.data(Qt.ItemDataRole.EditRole) or "")

    def setModelData(self, editor: QLineEdit, model, index: QModelIndex):
        model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)


class _SpinBoxDelegate(QStyledItemDelegate):
    """Delegate that provides a QSpinBox editor for a table cell."""

    def __init__(self, minimum: int, maximum: int, parent=None):
        super().__init__(parent)
        self._min = minimum
        self._max = maximum

    def createEditor(self, parent, option, index: QModelIndex):
        editor = QSpinBox(parent)
        editor.setMinimum(self._min)
        editor.setMaximum(self._max)
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor: QSpinBox, index: QModelIndex):
        val = index.data(Qt.ItemDataRole.EditRole)
        try:
            editor.setValue(int(val))
        except (TypeError, ValueError):
            editor.setValue(self._min)

    def setModelData(self, editor: QSpinBox, model, index: QModelIndex):
        model.setData(index, str(editor.value()), Qt.ItemDataRole.EditRole)


class _OptionalSpinBoxDelegate(QStyledItemDelegate):
    """Delegate for an optional integer field (empty string = None).

    Displays a QSpinBox with a special minimum value that represents 'empty'.
    The display text shows blank when the sentinel value is active.
    """

    _EMPTY_SENTINEL = 0  # stored as 0 in the spinbox to mean "no value"

    def __init__(self, minimum: int, maximum: int, parent=None):
        super().__init__(parent)
        self._min = minimum
        self._max = maximum

    def createEditor(self, parent, option, index: QModelIndex):
        editor = QSpinBox(parent)
        # Allow 0 as the "clear" value even though valid range starts at minimum
        editor.setMinimum(0)
        editor.setMaximum(self._max)
        editor.setSpecialValueText(" ")  # 0 displays as blank
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor: QSpinBox, index: QModelIndex):
        raw = index.data(Qt.ItemDataRole.EditRole)
        if raw is None or raw == "":
            editor.setValue(0)
        else:
            try:
                editor.setValue(int(raw))
            except (TypeError, ValueError):
                editor.setValue(0)

    def setModelData(self, editor: QSpinBox, model, index: QModelIndex):
        val = editor.value()
        # Store empty string for the sentinel (0 = no leap rule)
        model.setData(index, "" if val == 0 else str(val), Qt.ItemDataRole.EditRole)

    def displayText(self, value, locale) -> str:
        if value == "" or value is None:
            return ""
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return ""


# ---------------------------------------------------------------------------
# _MonthListEditor
# ---------------------------------------------------------------------------

# Column indices
_COL_UP = 0
_COL_DOWN = 1
_COL_NAME = 2
_COL_DAYS = 3
_COL_LEAP = 4


class _MonthListEditor(QWidget):
    """Upper half of the Months page — edits the list of MonthDefinitions."""

    changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._building = False  # guard against recursive signals during setup

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Table ---
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["", "", "Name", "Day Count", "Leap Every N Years"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )

        # Column sizing
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)

        # Delegates
        self._table.setItemDelegateForColumn(_COL_NAME, _LineEditDelegate(self))
        self._table.setItemDelegateForColumn(
            _COL_DAYS, _SpinBoxDelegate(5, 100, self)
        )
        self._table.setItemDelegateForColumn(
            _COL_LEAP, _OptionalSpinBoxDelegate(2, 999, self)
        )

        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        # --- Toolbar row: Add / Remove ---
        toolbar = QHBoxLayout()
        self._add_btn = QPushButton("Add Month")
        self._add_btn.clicked.connect(self._add_month)
        toolbar.addWidget(self._add_btn)

        self._remove_btn = QPushButton("Remove Month")
        self._remove_btn.clicked.connect(self._remove_month)
        toolbar.addWidget(self._remove_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # --- "Set all to same day count" row ---
        bulk_row = QHBoxLayout()
        bulk_row.addWidget(QLabel("Set all to same day count:"))
        self._bulk_spin = QSpinBox()
        self._bulk_spin.setMinimum(5)
        self._bulk_spin.setMaximum(100)
        self._bulk_spin.setValue(30)
        bulk_row.addWidget(self._bulk_spin)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_bulk_day_count)
        bulk_row.addWidget(apply_btn)
        bulk_row.addStretch()
        layout.addLayout(bulk_row)

        # Seed with one default month
        self._add_month()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_months(self) -> list[dict]:
        """Return list of dicts with keys: name, day_count, leap_every_n_years."""
        months = []
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, _COL_NAME)
            days_item = self._table.item(row, _COL_DAYS)
            leap_item = self._table.item(row, _COL_LEAP)

            name = name_item.text() if name_item else ""
            try:
                days = int(days_item.text()) if days_item and days_item.text() else 30
            except ValueError:
                days = 30
            leap_raw = leap_item.text() if leap_item else ""
            try:
                leap = int(leap_raw) if leap_raw.strip() else None
            except ValueError:
                leap = None

            months.append({"name": name, "day_count": days, "leap_every_n_years": leap})
        return months

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _add_month(self) -> None:
        self._building = True
        row = self._table.rowCount()
        self._table.insertRow(row)
        n = row + 1

        # Move Up button
        up_btn = QPushButton("▲")
        up_btn.setFixedWidth(28)
        up_btn.clicked.connect(lambda _, r=row: self._move_up(self._btn_row(up_btn)))
        self._table.setCellWidget(row, _COL_UP, up_btn)

        # Move Down button
        down_btn = QPushButton("▼")
        down_btn.setFixedWidth(28)
        down_btn.clicked.connect(lambda _, r=row: self._move_down(self._btn_row(down_btn)))
        self._table.setCellWidget(row, _COL_DOWN, down_btn)

        # Name
        name_item = QTableWidgetItem(f"Month {n}")
        self._table.setItem(row, _COL_NAME, name_item)

        # Day count
        days_item = QTableWidgetItem("30")
        days_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, _COL_DAYS, days_item)

        # Leap (empty = None)
        leap_item = QTableWidgetItem("")
        leap_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, _COL_LEAP, leap_item)

        self._building = False
        self._update_remove_btn()
        self.changed.emit()

    def _remove_month(self) -> None:
        if self._table.rowCount() <= 1:
            return
        row = self._table.currentRow()
        if row < 0:
            row = self._table.rowCount() - 1
        self._table.removeRow(row)
        self._update_remove_btn()
        self.changed.emit()

    def _move_up(self, row: int) -> None:
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self._table.selectRow(row - 1)
        self.changed.emit()

    def _move_down(self, row: int) -> None:
        if row >= self._table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self._table.selectRow(row + 1)
        self.changed.emit()

    def _apply_bulk_day_count(self) -> None:
        value = str(self._bulk_spin.value())
        self._building = True
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_DAYS)
            if item is None:
                item = QTableWidgetItem()
                self._table.setItem(row, _COL_DAYS, item)
            item.setText(value)
        self._building = False
        self.changed.emit()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._building:
            self.changed.emit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _btn_row(self, btn: QPushButton) -> int:
        """Find the current row index of a cell widget button."""
        for r in range(self._table.rowCount()):
            if self._table.cellWidget(r, _COL_UP) is btn:
                return r
            if self._table.cellWidget(r, _COL_DOWN) is btn:
                return r
        return -1

    def _swap_rows(self, row_a: int, row_b: int) -> None:
        """Swap the text content of two rows (not the cell widgets)."""
        for col in (_COL_NAME, _COL_DAYS, _COL_LEAP):
            item_a = self._table.item(row_a, col)
            item_b = self._table.item(row_b, col)
            text_a = item_a.text() if item_a else ""
            text_b = item_b.text() if item_b else ""
            if item_a is None:
                item_a = QTableWidgetItem()
                self._table.setItem(row_a, col, item_a)
            if item_b is None:
                item_b = QTableWidgetItem()
                self._table.setItem(row_b, col, item_b)
            item_a.setText(text_b)
            item_b.setText(text_a)

    def _update_remove_btn(self) -> None:
        self._remove_btn.setEnabled(self._table.rowCount() > 1)


# ---------------------------------------------------------------------------
# _IntercalaryEditor
# ---------------------------------------------------------------------------

# Column indices for intercalary table
_ICOL_NAME = 0
_ICOL_DAYS = 1
_ICOL_POS = 2
_ICOL_POS_LABEL = 3


class _IntercalaryEditor(QWidget):
    """Lower half of the Months page — edits IntercalaryPeriod entries."""

    changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._building = False
        self._month_names: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("<b>Intercalary Periods</b>"))

        # --- Table ---
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Day Count", "Position", "Position Label"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_ICOL_NAME, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_ICOL_POS_LABEL, QHeaderView.ResizeMode.Stretch)

        self._table.setItemDelegateForColumn(_ICOL_NAME, _LineEditDelegate(self))
        self._table.setItemDelegateForColumn(_ICOL_DAYS, _SpinBoxDelegate(1, 9999, self))

        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        self._add_btn = QPushButton("Add")
        self._add_btn.clicked.connect(self._add_period)
        toolbar.addWidget(self._add_btn)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._remove_period)
        toolbar.addWidget(self._remove_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._update_remove_btn()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_intercalary_periods(self) -> list[dict]:
        """Return list of dicts with keys: name, day_count, after_month (0-based int)."""
        periods = []
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, _ICOL_NAME)
            days_item = self._table.item(row, _ICOL_DAYS)
            pos_spin = self._table.cellWidget(row, _ICOL_POS)

            name = name_item.text() if name_item else ""
            try:
                days = int(days_item.text()) if days_item and days_item.text() else 1
            except ValueError:
                days = 1
            after_month = pos_spin.value() if pos_spin else 0

            periods.append({"name": name, "day_count": days, "after_month": after_month})
        return periods

    def refresh_months(self, month_names: list[str]) -> None:
        """Update position spinbox maximums and labels when the month list changes."""
        self._month_names = list(month_names)
        max_pos = len(self._month_names)
        for row in range(self._table.rowCount()):
            spin = self._table.cellWidget(row, _ICOL_POS)
            if spin is not None:
                current = spin.value()
                spin.setMaximum(max_pos)
                # Clamp to new max
                if current > max_pos:
                    spin.setValue(max_pos)
            self._update_pos_label(row)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _add_period(self) -> None:
        self._building = True
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Name
        name_item = QTableWidgetItem("Festival")
        self._table.setItem(row, _ICOL_NAME, name_item)

        # Day count
        days_item = QTableWidgetItem("1")
        days_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, _ICOL_DAYS, days_item)

        # Position spinbox (inline widget)
        spin = QSpinBox()
        spin.setMinimum(0)
        spin.setMaximum(len(self._month_names))
        spin.setValue(0)
        spin.setFrame(False)
        spin.valueChanged.connect(lambda _, r=row: self._on_pos_changed(r))
        self._table.setCellWidget(row, _ICOL_POS, spin)

        # Position label (read-only)
        label_item = QTableWidgetItem(self._pos_label_text(0))
        label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, _ICOL_POS_LABEL, label_item)

        self._building = False
        self._update_remove_btn()
        self.changed.emit()

    def _remove_period(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            row = self._table.rowCount() - 1
        if row < 0:
            return
        self._table.removeRow(row)
        self._update_remove_btn()
        self.changed.emit()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._building:
            self.changed.emit()

    def _on_pos_changed(self, row: int) -> None:
        self._update_pos_label(row)
        if not self._building:
            self.changed.emit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pos_label_text(self, position: int) -> str:
        """Return human-readable label for a position value."""
        if position == 0:
            return "Before all months"
        idx = position - 1
        if idx < len(self._month_names):
            return f"After {self._month_names[idx]}"
        return f"After month {position}"

    def _update_pos_label(self, row: int) -> None:
        spin = self._table.cellWidget(row, _ICOL_POS)
        label_item = self._table.item(row, _ICOL_POS_LABEL)
        if spin is None:
            return
        text = self._pos_label_text(spin.value())
        if label_item is None:
            label_item = QTableWidgetItem(text)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, _ICOL_POS_LABEL, label_item)
        else:
            label_item.setText(text)

    def _update_remove_btn(self) -> None:
        self._remove_btn.setEnabled(self._table.rowCount() > 0)


# ---------------------------------------------------------------------------
# Page 1 — Months
# ---------------------------------------------------------------------------

class _MonthsPage(_WizardPage):
    """Page 1 — Months (Month List Editor + Intercalary Editor)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("<b>Months</b>"))

        self._month_editor = _MonthListEditor()
        self._month_editor.changed.connect(self._on_months_changed)
        self._month_editor.changed.connect(self.changed)
        layout.addWidget(self._month_editor)

        self._intercalary_editor = _IntercalaryEditor()
        self._intercalary_editor.changed.connect(self.changed)
        layout.addWidget(self._intercalary_editor)

        # Seed the intercalary editor with the initial month list
        self._sync_intercalary_months()

    def _on_months_changed(self) -> None:
        self._sync_intercalary_months()

    def _sync_intercalary_months(self) -> None:
        month_names = [m["name"] for m in self._month_editor.get_months()]
        self._intercalary_editor.refresh_months(month_names)

    def validate(self) -> str | None:
        months = self._month_editor.get_months()
        if not (1 <= len(months) <= 30):
            return f"Month count must be between 1 and 30 (currently {len(months)})."
        for m in months:
            if not m["name"].strip():
                return "All months must have a non-empty name."
            if not (5 <= m["day_count"] <= 100):
                return f"Day count for '{m['name']}' must be between 5 and 100."
            leap = m["leap_every_n_years"]
            if leap is not None and leap < 2:
                return f"'Leap every N years' for '{m['name']}' must be ≥ 2."
        for p in self._intercalary_editor.get_intercalary_periods():
            if not p["name"].strip():
                return "All intercalary periods must have a non-empty name."
            if p["day_count"] < 1:
                return f"Day count for intercalary period '{p['name']}' must be ≥ 1."
        return None

    def collect(self) -> dict:
        return {
            "months": self._month_editor.get_months(),
            "intercalary_periods": self._intercalary_editor.get_intercalary_periods(),
        }


class _WeekPage(_WizardPage):
    """Page 2 — Week Structure."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("<b>Week Structure</b>"))

        # Week length spinbox
        length_row = QHBoxLayout()
        length_row.addWidget(QLabel("Week length (days):"))
        self._length_spin = QSpinBox()
        self._length_spin.setMinimum(1)
        self._length_spin.setMaximum(20)
        self._length_spin.setValue(7)
        length_row.addWidget(self._length_spin)
        length_row.addStretch()
        layout.addLayout(length_row)

        # Scroll area for weekday name inputs
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._names_container = QWidget()
        self._names_layout = QVBoxLayout(self._names_container)
        self._names_layout.setContentsMargins(4, 4, 4, 4)
        self._names_layout.addStretch()
        self._scroll.setWidget(self._names_container)
        layout.addWidget(self._scroll, stretch=1)

        self._name_edits: list[QLineEdit] = []

        # Build initial 7 weekday name inputs
        self._rebuild_names(7, [])

        # Connect signals after initial build
        self._length_spin.valueChanged.connect(self._on_length_changed)

    def _rebuild_names(self, new_length: int, existing: list[str]) -> None:
        """Rebuild the QLineEdit list to match new_length, preserving existing names."""
        # Remove old widgets
        for edit in self._name_edits:
            self._names_layout.removeWidget(edit)
            edit.deleteLater()
        self._name_edits = []

        # Remove the trailing stretch before re-adding widgets
        stretch_item = self._names_layout.takeAt(self._names_layout.count() - 1)

        for i in range(new_length):
            default = existing[i] if i < len(existing) else f"Day {i + 1}"
            edit = QLineEdit(default)
            edit.setPlaceholderText(f"Day {i + 1} name")
            edit.textChanged.connect(self.changed)
            self._names_layout.addWidget(edit)
            self._name_edits.append(edit)

        # Re-add the trailing stretch
        self._names_layout.addStretch()

    def _on_length_changed(self, value: int) -> None:
        existing = [e.text() for e in self._name_edits]
        self._rebuild_names(value, existing)
        self.changed.emit()

    def validate(self) -> str | None:
        length = self._length_spin.value()
        if not (1 <= length <= 20):
            return f"Week length must be between 1 and 20 (currently {length})."
        for i, edit in enumerate(self._name_edits):
            if not edit.text().strip():
                return f"Weekday {i + 1} name must not be empty."
        return None

    def collect(self) -> dict:
        return {
            "week_length": self._length_spin.value(),
            "weekday_names": [e.text() for e in self._name_edits],
        }


class _LunarPage(_WizardPage):
    """Page 3 — Lunar Cycles."""

    # Column indices
    _COL_NAME = 0
    _COL_INTERVAL = 1
    _COL_OFFSET = 2

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._building = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("<b>Lunar Cycles</b>"))

        # --- Table ---
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Name", "Phase Interval", "Phase Offset"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(self._COL_NAME, QHeaderView.ResizeMode.Stretch)

        self._table.setItemDelegateForColumn(self._COL_NAME, _LineEditDelegate(self))
        self._table.setItemDelegateForColumn(
            self._COL_INTERVAL, _SpinBoxDelegate(1, 9999, self)
        )
        self._table.setItemDelegateForColumn(
            self._COL_OFFSET, _SpinBoxDelegate(0, 9999, self)
        )

        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        self._add_btn = QPushButton("Add")
        self._add_btn.clicked.connect(self._add_cycle)
        toolbar.addWidget(self._add_btn)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._remove_cycle)
        toolbar.addWidget(self._remove_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._update_remove_btn()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_lunar_cycles(self) -> list[dict]:
        """Return list of dicts with keys: name, phase_interval, phase_offset."""
        cycles = []
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, self._COL_NAME)
            interval_item = self._table.item(row, self._COL_INTERVAL)
            offset_item = self._table.item(row, self._COL_OFFSET)

            name = name_item.text() if name_item else ""
            try:
                interval = int(interval_item.text()) if interval_item and interval_item.text() else 28
            except ValueError:
                interval = 28
            try:
                offset = int(offset_item.text()) if offset_item and offset_item.text() else 0
            except ValueError:
                offset = 0

            cycles.append({"name": name, "phase_interval": interval, "phase_offset": offset})
        return cycles

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _add_cycle(self) -> None:
        self._building = True
        row = self._table.rowCount()
        self._table.insertRow(row)

        name_item = QTableWidgetItem("Moon")
        self._table.setItem(row, self._COL_NAME, name_item)

        interval_item = QTableWidgetItem("28")
        interval_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, self._COL_INTERVAL, interval_item)

        offset_item = QTableWidgetItem("0")
        offset_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, self._COL_OFFSET, offset_item)

        self._building = False
        self._update_remove_btn()
        self.changed.emit()

    def _remove_cycle(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            row = self._table.rowCount() - 1
        if row < 0:
            return
        self._table.removeRow(row)
        self._update_remove_btn()
        self.changed.emit()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._building:
            self.changed.emit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_remove_btn(self) -> None:
        self._remove_btn.setEnabled(self._table.rowCount() > 0)

    # ------------------------------------------------------------------
    # _WizardPage interface
    # ------------------------------------------------------------------

    def validate(self) -> str | None:
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, self._COL_NAME)
            name = name_item.text() if name_item else ""
            if not name.strip():
                return f"Lunar cycle at row {row + 1} must have a non-empty name."

            interval_item = self._table.item(row, self._COL_INTERVAL)
            try:
                interval = int(interval_item.text()) if interval_item and interval_item.text() else 0
            except ValueError:
                interval = 0
            if interval < 1:
                return f"Phase interval for '{name or f'row {row + 1}'}' must be ≥ 1."

        return None

    def collect(self) -> dict:
        return {"lunar_cycles": self.get_lunar_cycles()}


# ---------------------------------------------------------------------------
# _EraEditor
# ---------------------------------------------------------------------------

# Column indices for era table
_ECOL_NAME = 0
_ECOL_YEAR = 1
_ECOL_DIR = 2


class _EraEditor(QWidget):
    """Sub-editor for the Eras section of Page 4.

    Displays a QTableWidget with columns: Name | Starting Year | Direction.
    Direction is an inline QComboBox (Ascending / Descending).
    Starting Year is an inline QSpinBox (1–9999).
    """

    changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._building = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("<b>Eras</b>"))

        # --- Table ---
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Name", "Starting Year", "Direction"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_ECOL_NAME, QHeaderView.ResizeMode.Stretch)

        self._table.setItemDelegateForColumn(_ECOL_NAME, _LineEditDelegate(self))

        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        self._add_btn = QPushButton("Add")
        self._add_btn.clicked.connect(self._add_era)
        toolbar.addWidget(self._add_btn)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._remove_era)
        toolbar.addWidget(self._remove_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._update_remove_btn()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_eras(self) -> list[dict]:
        """Return list of dicts with keys: name (str), starting_year (int), direction (str)."""
        eras = []
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, _ECOL_NAME)
            year_spin = self._table.cellWidget(row, _ECOL_YEAR)
            dir_combo = self._table.cellWidget(row, _ECOL_DIR)

            name = name_item.text() if name_item else ""
            starting_year = year_spin.value() if year_spin else 1
            direction_text = dir_combo.currentText() if dir_combo else "Ascending"
            direction = "ascending" if direction_text == "Ascending" else "descending"

            eras.append({"name": name, "starting_year": starting_year, "direction": direction})
        return eras

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _add_era(self) -> None:
        self._building = True
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Name
        name_item = QTableWidgetItem("Era 1")
        self._table.setItem(row, _ECOL_NAME, name_item)

        # Starting Year — inline QSpinBox
        year_spin = QSpinBox()
        year_spin.setMinimum(1)
        year_spin.setMaximum(9999)
        year_spin.setValue(1)
        year_spin.setFrame(False)
        year_spin.valueChanged.connect(lambda _: self._emit_changed())
        self._table.setCellWidget(row, _ECOL_YEAR, year_spin)

        # Direction — inline QComboBox
        dir_combo = QComboBox()
        dir_combo.addItems(["Ascending", "Descending"])
        dir_combo.currentIndexChanged.connect(lambda _: self._emit_changed())
        self._table.setCellWidget(row, _ECOL_DIR, dir_combo)

        self._building = False
        self._update_remove_btn()
        self.changed.emit()

    def _remove_era(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            row = self._table.rowCount() - 1
        if row < 0:
            return
        self._table.removeRow(row)
        self._update_remove_btn()
        self.changed.emit()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._building:
            self.changed.emit()

    def _emit_changed(self) -> None:
        if not self._building:
            self.changed.emit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_remove_btn(self) -> None:
        self._remove_btn.setEnabled(self._table.rowCount() > 0)


# ---------------------------------------------------------------------------
# _InitialDateEditor
# ---------------------------------------------------------------------------


class _InitialDateEditor(QWidget):
    """Sub-editor for the initial tracked date on Page 4.

    Contains numeric inputs for year, month, day, hour, minute, second, and
    an optional era dropdown (hidden when no eras are defined).

    Call ``refresh(month_list, era_names, hours_per_day)`` whenever the
    upstream data changes so that spinbox bounds stay in sync.
    """

    changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("<b>Initial Date</b>"))

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        # Year
        self._year_spin = QSpinBox()
        self._year_spin.setMinimum(1)
        self._year_spin.setMaximum(9999)
        self._year_spin.setValue(1)
        self._year_spin.valueChanged.connect(self._on_year_or_month_changed)
        form.addRow("Year:", self._year_spin)

        # Month
        self._month_spin = QSpinBox()
        self._month_spin.setMinimum(1)
        self._month_spin.setMaximum(1)  # updated by refresh()
        self._month_spin.setValue(1)
        self._month_spin.valueChanged.connect(self._on_year_or_month_changed)
        form.addRow("Month:", self._month_spin)

        # Day
        self._day_spin = QSpinBox()
        self._day_spin.setMinimum(1)
        self._day_spin.setMaximum(1)  # updated by refresh()
        self._day_spin.setValue(1)
        self._day_spin.valueChanged.connect(self.changed)
        form.addRow("Day:", self._day_spin)

        # Hour
        self._hour_spin = QSpinBox()
        self._hour_spin.setMinimum(0)
        self._hour_spin.setMaximum(23)  # updated by refresh()
        self._hour_spin.setValue(0)
        self._hour_spin.valueChanged.connect(self.changed)
        form.addRow("Hour:", self._hour_spin)

        # Minute
        self._minute_spin = QSpinBox()
        self._minute_spin.setMinimum(0)
        self._minute_spin.setMaximum(59)
        self._minute_spin.setValue(0)
        self._minute_spin.valueChanged.connect(self.changed)
        form.addRow("Minute:", self._minute_spin)

        # Second
        self._second_spin = QSpinBox()
        self._second_spin.setMinimum(0)
        self._second_spin.setMaximum(59)
        self._second_spin.setValue(0)
        self._second_spin.valueChanged.connect(self.changed)
        form.addRow("Second:", self._second_spin)

        # Era (hidden when no eras defined)
        self._era_label = QLabel("Era:")
        self._era_combo = QComboBox()
        self._era_combo.currentIndexChanged.connect(self.changed)
        form.addRow(self._era_label, self._era_combo)
        self._era_label.hide()
        self._era_combo.hide()

        layout.addLayout(form)

        # Internal state: current month list for day-bound calculation
        self._month_list: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(
        self,
        month_list: list[dict],
        era_names: list[str],
        hours_per_day: int,
    ) -> None:
        """Update spinbox bounds and era combo to reflect current wizard state.

        Parameters
        ----------
        month_list:
            List of month dicts with keys ``name``, ``day_count``, and
            ``leap_every_n_years`` (int or None).
        era_names:
            List of era name strings.  When empty the era combo is hidden.
        hours_per_day:
            The hours-per-day value from the calendar name/hours section.
        """
        self._month_list = list(month_list)

        # --- Month upper bound ---
        num_months = max(1, len(month_list))
        old_month = self._month_spin.value()
        self._month_spin.setMaximum(num_months)
        # Clamp if needed (setMaximum already clamps the value)

        # --- Day upper bound (depends on current month/year) ---
        self._update_day_max()

        # --- Hour upper bound ---
        max_hour = max(0, hours_per_day - 1)
        self._hour_spin.setMaximum(max_hour)
        if self._hour_spin.value() > max_hour:
            self._hour_spin.setValue(max_hour)

        # --- Era combo ---
        self._era_combo.blockSignals(True)
        self._era_combo.clear()
        if era_names:
            self._era_combo.addItems(era_names)
            self._era_label.show()
            self._era_combo.show()
        else:
            self._era_label.hide()
            self._era_combo.hide()
        self._era_combo.blockSignals(False)

    def get_date(self) -> dict:
        """Return a dict with keys: year, month, day, hour, minute, second, era_index.

        ``era_index`` is an ``int`` when an era is selected, or ``None`` when
        the era combo is hidden (no eras defined).
        """
        era_index: int | None = None
        if self._era_combo.isVisible() and self._era_combo.count() > 0:
            era_index = self._era_combo.currentIndex()
        return {
            "year": self._year_spin.value(),
            "month": self._month_spin.value(),
            "day": self._day_spin.value(),
            "hour": self._hour_spin.value(),
            "minute": self._minute_spin.value(),
            "second": self._second_spin.value(),
            "era_index": era_index,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _on_year_or_month_changed(self) -> None:
        """Recalculate day upper bound when year or month changes."""
        self._update_day_max()
        self.changed.emit()

    def _update_day_max(self) -> None:
        """Set the day spinbox maximum based on the selected month and year."""
        month_idx = self._month_spin.value() - 1  # 0-based
        year = self._year_spin.value()

        if 0 <= month_idx < len(self._month_list):
            month_data = self._month_list[month_idx]
            day_count = month_data.get("day_count", 30)
            leap_n = month_data.get("leap_every_n_years")
            if leap_n is not None and year % leap_n == 0:
                day_count += 1
        else:
            day_count = 30  # fallback before month list is populated

        self._day_spin.setMaximum(day_count)
        if self._day_spin.value() > day_count:
            self._day_spin.setValue(day_count)


class _ErasDateAndNamePage(_WizardPage):
    """Page 4 — Eras, Initial Date & Calendar Name."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Outer scroll area so the page is usable at small heights
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # --- Upper: Era Editor ---
        self._era_editor = _EraEditor()
        self._era_editor.changed.connect(self._on_eras_changed)
        self._era_editor.changed.connect(self.changed)
        layout.addWidget(self._era_editor)

        # --- Middle: Initial Date Editor ---
        self._date_editor = _InitialDateEditor()
        self._date_editor.changed.connect(self.changed)
        layout.addWidget(self._date_editor)

        # --- Lower: Calendar Name & Hours Per Day ---
        layout.addWidget(QLabel("<b>Calendar Details</b>"))

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. My Fantasy Calendar")
        self._name_edit.textChanged.connect(self.changed)
        form.addRow("Calendar Name:", self._name_edit)

        self._hours_spin = QSpinBox()
        self._hours_spin.setMinimum(1)
        self._hours_spin.setMaximum(99)
        self._hours_spin.setValue(24)
        self._hours_spin.valueChanged.connect(self._on_hours_changed)
        self._hours_spin.valueChanged.connect(self.changed)
        form.addRow("Hours Per Day:", self._hours_spin)

        layout.addLayout(form)
        layout.addStretch()

        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        # Seed the date editor with initial state
        self._refresh_date_editor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, month_list: list[dict]) -> None:
        """Called by the wizard when navigating to this page to sync month data."""
        self._month_list = list(month_list)
        self._refresh_date_editor()

    def get_calendar_name(self) -> str:
        return self._name_edit.text().strip()

    def get_hours_per_day(self) -> int:
        return self._hours_spin.value()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_eras_changed(self) -> None:
        self._refresh_date_editor()

    def _on_hours_changed(self) -> None:
        self._refresh_date_editor()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_date_editor(self) -> None:
        month_list = getattr(self, "_month_list", [])
        era_names = [e["name"] for e in self._era_editor.get_eras()]
        hours_per_day = self._hours_spin.value()
        self._date_editor.refresh(month_list, era_names, hours_per_day)

    # ------------------------------------------------------------------
    # _WizardPage interface
    # ------------------------------------------------------------------

    def validate(self) -> str | None:
        # --- Calendar name ---
        if not self._name_edit.text().strip():
            return "Calendar name must not be empty."

        # --- Hours per day ---
        hours = self._hours_spin.value()
        if not (1 <= hours <= 99):
            return f"Hours per day must be between 1 and 99 (currently {hours})."

        # --- Eras ---
        for era in self._era_editor.get_eras():
            if not era["name"].strip():
                return "All era names must be non-empty."
            if era["starting_year"] < 1:
                return f"Starting year for era '{era['name']}' must be ≥ 1."

        # --- Initial date: month index ---
        month_list = getattr(self, "_month_list", [])
        date = self._date_editor.get_date()
        month_val = date["month"]
        if month_val > len(month_list):
            return (
                f"Month {month_val} exceeds the number of defined months "
                f"({len(month_list)})."
            )

        # --- Initial date: day vs effective day count ---
        if month_list and 1 <= month_val <= len(month_list):
            month_data = month_list[month_val - 1]
            year_val = date["year"]
            day_count = month_data.get("day_count", 30)
            leap_n = month_data.get("leap_every_n_years")
            if leap_n is not None and year_val % leap_n == 0:
                day_count += 1
            if date["day"] > day_count:
                return (
                    f"Day {date['day']} exceeds the effective day count "
                    f"({day_count}) for the selected month and year."
                )

        return None

    def collect(self) -> dict:
        date = self._date_editor.get_date()
        eras = self._era_editor.get_eras()
        era_index = date.get("era_index")
        initial_date = {
            "year": date["year"],
            "month": date["month"],
            "day": date["day"],
            "hour": date["hour"],
            "minute": date["minute"],
            "second": date["second"],
            "era_index": era_index,
        }
        return {
            "calendar_name": self._name_edit.text().strip(),
            "hours_per_day": self._hours_spin.value(),
            "eras": eras,
            "initial_date": initial_date,
        }


# ---------------------------------------------------------------------------
# Main wizard dialog
# ---------------------------------------------------------------------------

_PAGE_NAMES = [
    "Months",
    "Week Structure",
    "Lunar Cycles",
    "Eras, Initial Date & Calendar Name",
]


class CalendarWizardDialog(QDialog):
    """Multi-step wizard for building a CalendarDefinition."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Fantasy Calendar")
        self.setMinimumSize(640, 480)

        self._calendar: CalendarDefinition | None = None
        self._initial_date: FantasyDateTime | None = None

        # --- Build pages ---
        self._pages: list[_WizardPage] = [
            _MonthsPage(),
            _WeekPage(),
            _LunarPage(),
            _ErasDateAndNamePage(),
        ]

        # --- Root layout ---
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # 1. Header label
        self._header_label = QLabel()
        self._header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        root.addWidget(self._header_label)

        # 2. Stacked page area
        self._stack = QStackedWidget()
        for page in self._pages:
            self._stack.addWidget(page)
            page.changed.connect(self._update_nav)
        root.addWidget(self._stack, stretch=1)

        # 3. Validation error label
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        root.addWidget(self._error_label)

        # 4. Button row: Back | spacer | Cancel | Next/Finish
        btn_row = QHBoxLayout()

        self._back_btn = QPushButton("Back")
        self._back_btn.clicked.connect(self._go_back)
        btn_row.addWidget(self._back_btn)

        btn_row.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.clicked.connect(self._go_next)
        btn_row.addWidget(self._next_btn)

        root.addLayout(btn_row)

        # Initialise header and button states for page 0
        self._update_header()
        self._update_nav()

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _current_index(self) -> int:
        return self._stack.currentIndex()

    def _current_page(self) -> _WizardPage:
        return self._pages[self._current_index()]

    def _go_next(self) -> None:
        """Advance to the next page, or finish if on the last page."""
        page = self._current_page()
        error = page.validate()
        if error:
            self._show_error(error)
            return

        idx = self._current_index()
        if idx < len(self._pages) - 1:
            next_idx = idx + 1
            self._stack.setCurrentIndex(next_idx)
            # When navigating to page 4 (index 3), sync month list from page 1
            if next_idx == 3:
                month_list = self._pages[0].collect()["months"]
                self._pages[3].refresh(month_list)
            self._update_header()
            self._clear_error()
            self._update_nav()
        else:
            self._on_finish()

    def _go_back(self) -> None:
        """Return to the previous page."""
        idx = self._current_index()
        if idx > 0:
            self._stack.setCurrentIndex(idx - 1)
            self._update_header()
            self._clear_error()
            self._update_nav()

    def _on_finish(self) -> None:
        """Validate all pages, build the result, and accept the dialog."""
        for i, page in enumerate(self._pages):
            error = page.validate()
            if error:
                self._stack.setCurrentIndex(i)
                self._update_header()
                self._show_error(error)
                self._update_nav()
                return
        self._build_and_save()

    def _update_nav(self) -> None:
        """Enable/disable Back and Next/Finish based on current page state."""
        idx = self._current_index()
        is_last = idx == len(self._pages) - 1

        # Back button: hidden on first page
        self._back_btn.setVisible(idx > 0)

        # Next/Finish label
        self._next_btn.setText("Finish" if is_last else "Next")

        # Enable Next/Finish only when current page is valid
        error = self._current_page().validate()
        self._next_btn.setEnabled(error is None)

        # Show/clear error message in sync
        if error:
            self._show_error(error)
        else:
            self._clear_error()

    def _update_header(self) -> None:
        idx = self._current_index()
        page_name = _PAGE_NAMES[idx]
        total = len(self._pages)
        self._header_label.setText(f"Step {idx + 1} of {total}: {page_name}")

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()

    def _clear_error(self) -> None:
        self._error_label.hide()
        self._error_label.clear()

    # ------------------------------------------------------------------
    # Build & save
    # ------------------------------------------------------------------

    def _build_and_save(self) -> None:
        """Assemble CalendarDefinition and FantasyDateTime, save JSON, accept."""
        # Collect data from all pages
        page0 = self._pages[0].collect()   # months, intercalary_periods
        page1 = self._pages[1].collect()   # week_length, weekday_names
        page2 = self._pages[2].collect()   # lunar_cycles
        page3 = self._pages[3].collect()   # calendar_name, hours_per_day, eras, initial_date

        # --- Construct model objects ---
        try:
            months = [
                MonthDefinition(
                    name=m["name"],
                    day_count=m["day_count"],
                    leap_every_n_years=m["leap_every_n_years"],
                )
                for m in page0["months"]
            ]

            intercalary_periods = [
                IntercalaryPeriod(
                    name=p["name"],
                    day_count=p["day_count"],
                    after_month=p["after_month"],
                )
                for p in page0["intercalary_periods"]
            ]

            lunar_cycles = [
                LunarCycle(
                    name=lc["name"],
                    phase_interval=lc["phase_interval"],
                    phase_offset=lc["phase_offset"],
                )
                for lc in page2["lunar_cycles"]
            ]

            eras = [
                Era(
                    name=e["name"],
                    starting_year=e["starting_year"],
                    direction=EraDirection(e["direction"]),
                )
                for e in page3["eras"]
            ]

            calendar_def = CalendarDefinition(
                name=page3["calendar_name"],
                months=months,
                week_length=page1["week_length"],
                weekday_names=page1["weekday_names"],
                hours_per_day=page3["hours_per_day"],
                lunar_cycles=lunar_cycles,
                intercalary_periods=intercalary_periods,
                eras=eras,
            )
        except (ValueError, KeyError) as exc:
            QMessageBox.critical(self, "Calendar Error", f"Failed to build calendar: {exc}")
            return

        # --- Construct FantasyDateTime ---
        initial_date = page3["initial_date"]
        era_index = initial_date.get("era_index")
        era_obj: Era | None = eras[era_index] if (era_index is not None and 0 <= era_index < len(eras)) else None

        try:
            initial_dt = FantasyDateTime(
                calendar=calendar_def,
                year=initial_date["year"],
                month=initial_date["month"],
                day=initial_date["day"],
                hour=initial_date["hour"],
                minute=initial_date["minute"],
                second=initial_date["second"],
                era=era_obj,
            )
        except (ValueError, KeyError) as exc:
            QMessageBox.critical(self, "Date Error", f"Failed to build initial date: {exc}")
            return

        # --- Sanitize filename ---
        raw_name = page3["calendar_name"]
        sanitized = re.sub(r"[^A-Za-z0-9\-_]", "_", raw_name).lower()
        filename = sanitized + ".json"
        target_path = Path("assets/calendars") / filename

        # --- Overwrite check ---
        if target_path.exists():
            reply = QMessageBox.question(
                self,
                "Overwrite Calendar?",
                f"A calendar file named '{filename}' already exists.\nOverwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return  # stay open on last page

        # --- Serialize to JSON ---
        # Use dataclasses.asdict then convert EraDirection enums to their string values
        raw_dict = dataclasses.asdict(calendar_def)

        def _convert_enums(obj):
            if isinstance(obj, dict):
                return {k: _convert_enums(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_convert_enums(item) for item in obj]
            if hasattr(obj, "value"):  # Enum
                return obj.value
            return obj

        serializable = _convert_enums(raw_dict)

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=4)
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save calendar file:\n{exc}")
            return

        # --- Store results and accept ---
        self._calendar = calendar_def
        self._initial_date = initial_dt
        self.accept()

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_calendar(self) -> CalendarDefinition | None:
        """Return the built CalendarDefinition after Accepted, else None."""
        return self._calendar

    def get_initial_date(self) -> FantasyDateTime | None:
        """Return the initial FantasyDateTime after Accepted, else None."""
        return self._initial_date
