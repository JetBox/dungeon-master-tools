from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSpinBox
from PyQt6.QtCore import QTimer

_FLASH_MS = 80


class TimeRandomEncounterWidget(QFrame):
    """Fixed widget pinned to the top of the Time Mode scroll area.

    Interval is stored in minutes; the internal counter runs in seconds.
    ``decrement(seconds)`` subtracts seconds from the counter, floors at 0,
    and returns True when the counter reaches zero (caller plays the sound).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self._base_style = "TimeRandomEncounterWidget { border: 2px solid #F44336; }"
        self.setStyleSheet(self._base_style)
        self._interval_minutes = 12
        self._counter = self._interval_minutes * 60  # seconds
        self._expired = False

        row = QHBoxLayout(self)

        row.addWidget(QLabel("⚔️"))
        row.addWidget(QLabel("Random Encounter"))

        row.addWidget(QLabel(" Interval (min):"))
        self._interval_spin = QSpinBox()
        self._interval_spin.setMinimum(0)
        self._interval_spin.setMaximum(60)
        self._interval_spin.setValue(self._interval_minutes)
        self._interval_spin.valueChanged.connect(self._on_interval_changed)
        row.addWidget(self._interval_spin)

        row.addStretch()

        self._counter_label = QLabel(self._format_counter())
        row.addWidget(self._counter_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decrement(self, seconds: int) -> bool:
        """Subtract *seconds* from the counter, floor at 0.

        Returns True if this call caused the counter to reach zero (expiry).
        On expiry ``reset()`` is called automatically; the caller is
        responsible for playing the RE sound.
        """
        if self._expired or self._interval_minutes == 0:
            return False
        if self._counter == 0:
            return False
        self._counter = max(0, self._counter - seconds)
        self._counter_label.setText(self._format_counter())
        if self._counter == 0:
            self._on_expired()
            return True
        return False

    def reset(self) -> None:
        """Reset counter back to ``interval_minutes × 60`` seconds."""
        self._expired = False
        self._counter = self._interval_minutes * 60
        self._counter_label.setStyleSheet("")
        self._counter_label.setText(self._format_counter())
        self.setStyleSheet(self._base_style)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _format_counter(self) -> str:
        h, rem = divmod(self._counter, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _on_interval_changed(self, value: int) -> None:
        self._interval_minutes = value
        if value == 0:
            self.hide()
        else:
            self.show()
            if self._expired:
                self.reset()
            else:
                self._counter = value * 60
                self._counter_label.setText(self._format_counter())

    def _on_expired(self) -> None:
        self._counter_label.setStyleSheet("QLabel { color: gray; }")
        self._flash(6)
        self.reset()

    def _flash(self, remaining: int) -> None:
        if remaining <= 0:
            self.setStyleSheet(self._base_style)
            return
        highlight = remaining % 2 == 0
        style = (
            "TimeRandomEncounterWidget { border: 2px solid #F44336; background-color: orange; }"
            if highlight
            else self._base_style
        )
        self.setStyleSheet(style)
        QTimer.singleShot(_FLASH_MS, lambda: self._flash(remaining - 1))
