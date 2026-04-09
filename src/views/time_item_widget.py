from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton
)
from PyQt6.QtCore import pyqtSignal, QTimer

from src.models import TimeTrackerItem, CATEGORY_STYLE

_FLASH_MS = 80


def _format_hms(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


class TimeItemWidget(QFrame):
    delete_requested = pyqtSignal(object)  # emits self

    def __init__(self, item: TimeTrackerItem, parent=None) -> None:
        super().__init__(parent)

        border_color, emoji = CATEGORY_STYLE[item.category]
        self._border_color = border_color
        self._base_style = f"TimeItemWidget {{ border: 2px solid {border_color}; }}"
        self.setStyleSheet(self._base_style)

        self._last_valid_name = item.name
        self._paused = False
        self._expired = False

        row = QHBoxLayout(self)

        if emoji:
            row.addWidget(QLabel(emoji))

        self._name_edit = QLineEdit(item.name)
        self._name_edit.editingFinished.connect(self._on_name_editing_finished)
        row.addWidget(self._name_edit)

        self._hms_label = QLabel(_format_hms(item.seconds))
        row.addWidget(self._hms_label)

        self._spin = QSpinBox()
        self._spin.setMinimum(0)
        self._spin.setMaximum(999999)
        self._spin.setValue(item.seconds)
        self._spin.valueChanged.connect(self._on_value_changed)
        row.addWidget(self._spin)

        self._pause_btn = QPushButton("⏸")
        self._pause_btn.setFixedSize(28, 28)
        self._pause_btn.setCheckable(True)
        self._pause_btn.clicked.connect(self._on_pause)
        row.addWidget(self._pause_btn)

        self._delete_btn = QPushButton("X")
        self._delete_btn.setFixedSize(28, 28)
        self._delete_btn.clicked.connect(self._on_delete)
        row.addWidget(self._delete_btn)

    def _on_name_editing_finished(self) -> None:
        text = self._name_edit.text()
        if text.strip():
            self._last_valid_name = text
        else:
            self._name_edit.setText(self._last_valid_name)

    def _on_pause(self, checked: bool) -> None:
        self._paused = checked
        self._name_edit.setEnabled(not checked)
        self._spin.setEnabled(not checked)
        self.setStyleSheet(
            f"TimeItemWidget {{ border: 2px solid {self._border_color}; opacity: {'0.4' if checked else '1.0'}; }}"
        )

    def _on_value_changed(self, value: int) -> None:
        self._hms_label.setText(_format_hms(value))
        if value > 0 and self._expired:
            self._expired = False
            self._spin.setStyleSheet("")
            self.setStyleSheet(self._base_style)

    def _on_delete(self) -> None:
        self.delete_requested.emit(self)

    def _on_expired(self) -> None:
        self._expired = True
        self._spin.setStyleSheet("QSpinBox { color: gray; }")
        self._flash(6)

    def _flash(self, remaining: int) -> None:
        if remaining <= 0:
            self.setStyleSheet(self._base_style)
            return
        highlight = remaining % 2 == 0
        style = (
            f"TimeItemWidget {{ border: 2px solid {self._border_color}; background-color: orange; }}"
            if highlight else self._base_style
        )
        self.setStyleSheet(style)
        QTimer.singleShot(_FLASH_MS, lambda: self._flash(remaining - 1))

    def decrement(self, seconds: int) -> bool:
        """Subtract `seconds` from remaining, floor at 0.
        Returns True if this call caused expiry."""
        if self._paused or self._expired:
            return False
        prev = self._spin.value()
        if prev == 0:
            return False
        new_val = max(0, prev - seconds)
        self._spin.setValue(new_val)
        if new_val == 0:
            self._on_expired()
            return True
        return False

    def get_seconds(self) -> int:
        """Return current remaining seconds (for sorting)."""
        return self._spin.value()

    def is_paused(self) -> bool:
        return self._paused
