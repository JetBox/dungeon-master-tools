from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSpinBox
from PyQt6.QtCore import QTimer

_FLASH_MS = 80


class RandomEncounterWidget(QFrame):
    """Fixed widget always pinned to the top of the scroll area."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self._base_style = "RandomEncounterWidget { border: 2px solid #F44336; }"
        self.setStyleSheet(self._base_style)
        self._interval = 2
        self._expired = False

        row = QHBoxLayout(self)

        row.addWidget(QLabel("⚔️"))
        row.addWidget(QLabel("Random Encounter"))

        row.addStretch()

        self._spin = QSpinBox()
        self._spin.setMinimum(0)
        self._spin.setValue(self._interval)
        self._spin.valueChanged.connect(self._on_value_changed)
        row.addWidget(self._spin)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_interval(self, value: int) -> None:
        """Update the interval and reset the counter."""
        self._interval = value
        if not self._expired:
            self._spin.setValue(value)

    def decrement(self) -> bool:
        """Decrement by 1. Returns True if this call caused it to reach 0."""
        if self._expired or self._interval == 0:
            return False
        prev = self._spin.value()
        if prev == 0:
            return False
        self._spin.setValue(prev - 1)
        if self._spin.value() == 0:
            self._on_expired()
            return True
        return False

    def reset(self) -> None:
        """Reset counter back to the current interval."""
        self._expired = False
        self._spin.setStyleSheet("")
        self.setStyleSheet(self._base_style)
        self._spin.setValue(self._interval)

    # ------------------------------------------------------------------
    # Private slots
    # ------------------------------------------------------------------

    def _on_value_changed(self, value: int) -> None:
        if value > 0 and self._expired:
            self._expired = False
            self._spin.setStyleSheet("")
            self.setStyleSheet(self._base_style)

    def _on_expired(self) -> None:
        self._expired = True
        self._spin.setStyleSheet("QSpinBox { color: gray; }")
        self._flash(6)

    def _flash(self, remaining: int) -> None:
        if remaining <= 0:
            self.setStyleSheet(self._base_style)
            return
        highlight = remaining % 2 == 0
        style = "RandomEncounterWidget { border: 2px solid #F44336; background-color: orange; }" if highlight else self._base_style
        self.setStyleSheet(style)
        QTimer.singleShot(_FLASH_MS, lambda: self._flash(remaining - 1))
