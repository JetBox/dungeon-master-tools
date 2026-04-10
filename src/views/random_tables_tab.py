import random

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.models import RandomTable, TableEntry


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def weighted_roll(entries: list[TableEntry]) -> TableEntry | None:
    """Return one entry selected proportionally to weight, or None if empty."""
    if not entries:
        return None
    total = sum(e.weight for e in entries)
    r = random.uniform(0, total)
    cumulative = 0.0
    for entry in entries:
        cumulative += entry.weight
        if r <= cumulative:
            return entry
    return entries[-1]  # guard against floating-point edge


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------

class AddTableDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Table")

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._name_edit = QLineEdit()
        form.addRow("Table name:", self._name_edit)
        layout.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_name(self) -> str:
        return self._name_edit.text().strip()

    def _on_accept(self) -> None:
        if not self._name_edit.text().strip():
            self._error_label.setText("Name cannot be empty.")
            self._error_label.show()
            return
        self.accept()


class AddEntryDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Entry")

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._name_edit = QLineEdit()
        form.addRow("Entry name:", self._name_edit)

        self._weight_spin = QSpinBox()
        self._weight_spin.setMinimum(1)
        self._weight_spin.setValue(1)
        form.addRow("Weight:", self._weight_spin)

        layout.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_entry(self) -> TableEntry:
        return TableEntry(
            name=self._name_edit.text().strip(),
            weight=self._weight_spin.value(),
        )

    def _on_accept(self) -> None:
        if not self._name_edit.text().strip():
            self._error_label.setText("Name cannot be empty.")
            self._error_label.show()
            return
        if self._weight_spin.value() < 1:
            self._error_label.setText("Weight must be at least 1.")
            self._error_label.show()
            return
        self.accept()


# ---------------------------------------------------------------------------
# EntryWidget
# ---------------------------------------------------------------------------

_ENTRY_FLASH_MS = 80


class EntryWidget(QFrame):
    delete_requested = pyqtSignal(object)   # self
    edit_mode_entered = pyqtSignal(object)  # self
    edit_mode_exited = pyqtSignal(object)   # self

    _BASE_STYLE = "EntryWidget { border: 1px solid #888; }"
    _FLASH_STYLE = "EntryWidget { border: 1px solid #888; background-color: orange; }"

    def __init__(self, entry: TableEntry, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(self._BASE_STYLE)
        self._entry = entry
        self._edit_mode = False

        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(4, 2, 4, 2)

        # --- read-only widgets ---
        self._weight_label = QLabel(str(entry.weight))
        self._weight_label.setFixedWidth(36)
        self._row.addWidget(self._weight_label)

        self._name_label = QLabel(entry.name)
        self._row.addWidget(self._name_label, stretch=1)

        self._edit_btn = QPushButton("📝")
        self._edit_btn.setFixedSize(40, 28)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._row.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("X")
        self._delete_btn.setFixedSize(28, 28)
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        self._row.addWidget(self._delete_btn)

        # --- edit-mode widgets (hidden initially) ---
        self._weight_spin = QSpinBox()
        self._weight_spin.setMinimum(1)
        self._weight_spin.setFixedWidth(60)
        self._weight_spin.hide()
        self._row.insertWidget(0, self._weight_spin)

        self._name_edit = QLineEdit()
        self._name_edit.hide()
        self._row.insertWidget(1, self._name_edit)

        self._save_btn = QPushButton("💾")
        self._save_btn.setFixedSize(40, 28)
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._save_btn.hide()
        self._row.addWidget(self._save_btn)

        self._error_label = QLabel("!")
        self._error_label.setStyleSheet("color: red; font-weight: bold;")
        self._error_label.setToolTip("Name cannot be empty and weight must be >= 1.")
        self._error_label.hide()
        self._row.addWidget(self._error_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_in_edit_mode(self) -> bool:
        return self._edit_mode

    def flash(self) -> None:
        self._flash(6)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_edit_clicked(self) -> None:
        self._edit_mode = True

        # populate edit widgets
        self._weight_spin.setValue(self._entry.weight)
        self._name_edit.setText(self._entry.name)

        # swap display
        self._weight_label.hide()
        self._name_label.hide()
        self._edit_btn.hide()

        self._weight_spin.show()
        self._name_edit.show()
        self._save_btn.show()

        self.edit_mode_entered.emit(self)

    def _on_save_clicked(self) -> None:
        name = self._name_edit.text().strip()
        weight = self._weight_spin.value()

        if not name or weight < 1:
            self._error_label.show()
            return

        self._error_label.hide()

        # persist to model
        self._entry.name = name
        self._entry.weight = weight

        # update read-only labels
        self._name_label.setText(name)
        self._weight_label.setText(str(weight))

        # swap back to display mode
        self._weight_spin.hide()
        self._name_edit.hide()
        self._save_btn.hide()

        self._weight_label.show()
        self._name_label.show()
        self._edit_btn.show()

        self._edit_mode = False
        self.edit_mode_exited.emit(self)

    def _flash(self, remaining: int) -> None:
        if remaining <= 0:
            self.setStyleSheet(self._BASE_STYLE)
            return
        highlight = remaining % 2 == 0
        self.setStyleSheet(self._FLASH_STYLE if highlight else self._BASE_STYLE)
        QTimer.singleShot(_ENTRY_FLASH_MS, lambda: self._flash(remaining - 1))


# ---------------------------------------------------------------------------
# TableListItem
# ---------------------------------------------------------------------------


class TableListItem(QFrame):
    selected = pyqtSignal(object)           # RandomTable
    name_changed = pyqtSignal(object, str)  # RandomTable, new_name

    _BASE_STYLE = "TableListItem { border: 1px solid transparent; padding: 2px; }"
    _SELECTED_STYLE = "TableListItem { border: 1px solid #555; background-color: #d0e8ff; padding: 2px; }"

    def __init__(self, table: RandomTable, parent=None) -> None:
        super().__init__(parent)
        self._table = table
        self.setStyleSheet(self._BASE_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(4, 2, 4, 2)

        self._name_label = QLabel(table.name)
        self._row.addWidget(self._name_label, stretch=1)

        self._edit_btn = QPushButton("📝")
        self._edit_btn.setFixedSize(40, 24)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._row.addWidget(self._edit_btn)

        # edit-mode widget (hidden initially)
        self._name_edit = QLineEdit()
        self._name_edit.hide()
        self._row.insertWidget(0, self._name_edit)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_selected(self, selected: bool) -> None:
        self.setStyleSheet(self._SELECTED_STYLE if selected else self._BASE_STYLE)

    # ------------------------------------------------------------------
    # Events / slots
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self._table)
        super().mousePressEvent(event)

    def _on_edit_clicked(self) -> None:
        self._name_edit.setText(self._table.name)
        self._name_label.hide()
        self._edit_btn.hide()
        self._name_edit.show()
        self._name_edit.setFocus()
        self._name_edit.selectAll()
        self._name_edit.editingFinished.connect(self._on_name_editing_finished)

    def _on_name_editing_finished(self) -> None:
        self._name_edit.editingFinished.disconnect(self._on_name_editing_finished)
        new_name = self._name_edit.text().strip()
        if not new_name:
            # revert
            self._name_edit.hide()
            self._name_label.show()
            self._edit_btn.show()
            return
        self._table.name = new_name
        self._name_label.setText(new_name)
        self._name_edit.hide()
        self._name_label.show()
        self._edit_btn.show()
        self.name_changed.emit(self._table, new_name)


# ---------------------------------------------------------------------------
# TableListSidebar
# ---------------------------------------------------------------------------

class TableListSidebar(QWidget):
    table_selected = pyqtSignal(object)  # RandomTable

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[TableListItem] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        add_btn = QPushButton("+")
        add_btn.setFixedHeight(28)
        add_btn.clicked.connect(self._on_add_clicked)
        outer.addWidget(add_btn)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)

        container = QWidget()
        self._list_layout = QVBoxLayout(container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._list_layout.addSpacerItem(self._spacer)
        self._scroll.setWidget(container)

        # internal signal for the "+" button — wired by RandomTablesTab
        self._add_clicked_callback = None

    def _on_add_clicked(self) -> None:
        if self._add_clicked_callback:
            self._add_clicked_callback()

    def set_add_callback(self, callback) -> None:
        """Allow the parent tab to hook the '+' button."""
        self._add_clicked_callback = callback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_table(self, table: RandomTable) -> None:
        item = TableListItem(table)
        item.selected.connect(self.select_table)
        item.name_changed.connect(lambda t, n: None)  # parent can connect further
        # insert before the trailing spacer
        idx = self._list_layout.count() - 1
        self._list_layout.insertWidget(idx, item)
        self._items.append(item)
        self.select_table(table)

    def select_table(self, table: RandomTable) -> None:
        for item in self._items:
            item.set_selected(item._table is table)
        self.table_selected.emit(table)


# ---------------------------------------------------------------------------
# TableContentArea
# ---------------------------------------------------------------------------

class TableContentArea(QWidget):
    add_entry_requested = pyqtSignal()
    roll_requested = pyqtSignal()
    edit_mode_changed = pyqtSignal(bool)  # True = some entry is in edit mode

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entry_widgets: list[EntryWidget] = []
        self._edit_mode_count = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Toolbar (hidden until a table is selected)
        self._toolbar_widget = QWidget()
        toolbar = QVBoxLayout(self._toolbar_widget)
        toolbar.setContentsMargins(4, 4, 4, 4)
        toolbar.setSpacing(4)

        self._roll_btn = QPushButton("Roll")
        self._roll_btn.clicked.connect(self.roll_requested.emit)
        toolbar.addWidget(self._roll_btn)

        self._last_roll_label = QLabel("")
        self._last_roll_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._last_roll_label.setStyleSheet("color: #555; font-style: italic;")
        toolbar.addWidget(self._last_roll_label)

        self._toolbar_widget.hide()
        outer.addWidget(self._toolbar_widget)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)

        self._container = QWidget()
        self._entries_layout = QVBoxLayout(self._container)
        self._entries_layout.setContentsMargins(0, 0, 0, 0)
        self._entries_layout.setSpacing(2)

        # "+" button lives inside the scroll area, below entries
        self._add_btn = QPushButton("+")
        self._add_btn.setMinimumHeight(36)
        self._add_btn.clicked.connect(self.add_entry_requested.emit)
        self._entries_layout.addWidget(self._add_btn)

        self._spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._entries_layout.addSpacerItem(self._spacer)
        self._scroll.setWidget(self._container)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, table: RandomTable) -> None:
        """Clear existing widgets and rebuild from table.entries."""
        self.clear()
        self._toolbar_widget.show()
        for entry in table.entries:
            widget = EntryWidget(entry)
            widget.edit_mode_entered.connect(self._on_edit_mode_entered)
            widget.edit_mode_exited.connect(self._on_edit_mode_exited)
            # insert before the "+" button (second-to-last) and spacer (last)
            idx = self._entries_layout.count() - 2
            self._entries_layout.insertWidget(idx, widget)
            self._entry_widgets.append(widget)

    def clear(self) -> None:
        """Remove all entry widgets."""
        for widget in self._entry_widgets:
            self._entries_layout.removeWidget(widget)
            widget.deleteLater()
        self._entry_widgets.clear()
        self._edit_mode_count = 0
        self._last_roll_label.setText("")
        self._toolbar_widget.hide()

    def set_roll_enabled(self, enabled: bool) -> None:
        self._roll_btn.setEnabled(enabled)

    def set_last_roll(self, name: str) -> None:
        self._last_roll_label.setText(f"Last roll: {name}")

    def scroll_to(self, widget: EntryWidget) -> None:
        self._scroll.ensureWidgetVisible(widget)

    def widget_for_entry(self, entry: TableEntry) -> "EntryWidget | None":
        for w in self._entry_widgets:
            if w._entry is entry:
                return w
        return None

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_edit_mode_entered(self, widget: EntryWidget) -> None:
        self._edit_mode_count += 1
        if self._edit_mode_count == 1:
            self.edit_mode_changed.emit(True)

    def _on_edit_mode_exited(self, widget: EntryWidget) -> None:
        self._edit_mode_count = max(0, self._edit_mode_count - 1)
        if self._edit_mode_count == 0:
            self.edit_mode_changed.emit(False)


# ---------------------------------------------------------------------------
# RandomTablesTab
# ---------------------------------------------------------------------------

class RandomTablesTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._tables: list[RandomTable] = []
        self._selected_table: RandomTable | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._sidebar = TableListSidebar()
        self._sidebar.setFixedWidth(200)
        self._sidebar.table_selected.connect(self._on_table_selected)
        self._sidebar.set_add_callback(self._on_add_table)
        layout.addWidget(self._sidebar)

        self._content_area = TableContentArea()
        self._content_area.add_entry_requested.connect(self._on_add_entry)
        self._content_area.roll_requested.connect(self._on_roll)
        self._content_area.edit_mode_changed.connect(self._on_edit_mode_changed)
        layout.addWidget(self._content_area, stretch=1)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_add_table(self) -> None:
        dialog = AddTableDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        table = RandomTable(name=dialog.get_name())
        self._tables.append(table)
        self._sidebar.add_table(table)

    def _on_table_selected(self, table: RandomTable) -> None:
        self._selected_table = table
        self._content_area.populate(table)

    def _on_add_entry(self) -> None:
        if self._selected_table is None:
            return
        dialog = AddEntryDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        entry = dialog.get_entry()
        self._selected_table.entries.append(entry)
        widget = EntryWidget(entry)
        widget.delete_requested.connect(self._on_delete_entry)
        widget.edit_mode_entered.connect(self._content_area._on_edit_mode_entered)
        widget.edit_mode_exited.connect(self._content_area._on_edit_mode_exited)
        # insert before "+" button (second-to-last) and spacer (last)
        idx = self._content_area._entries_layout.count() - 2
        self._content_area._entries_layout.insertWidget(idx, widget)
        self._content_area._entry_widgets.append(widget)

    def _on_delete_entry(self, widget: EntryWidget) -> None:
        if self._selected_table is None:
            return
        entry = widget._entry
        if entry in self._selected_table.entries:
            self._selected_table.entries.remove(entry)
        if widget in self._content_area._entry_widgets:
            self._content_area._entry_widgets.remove(widget)
        self._content_area._entries_layout.removeWidget(widget)
        widget.deleteLater()

    def _on_roll(self) -> None:
        if self._selected_table is None:
            return
        if not self._selected_table.entries:
            return
        if any(w.is_in_edit_mode() for w in self._content_area._entry_widgets):
            return
        result = weighted_roll(self._selected_table.entries)
        if result is None:
            return
        widget = self._content_area.widget_for_entry(result)
        if widget is None:
            return
        self._content_area.scroll_to(widget)
        self._content_area.set_last_roll(result.name)
        widget.flash()

    def _on_edit_mode_changed(self, active: bool) -> None:
        self._content_area.set_roll_enabled(not active)
