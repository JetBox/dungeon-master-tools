from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QButtonGroup,
    QRadioButton,
    QHBoxLayout,
    QVBoxLayout,
)

from src.models import TimeTrackerItem, ItemCategory, CATEGORY_STYLE


class AddTimeItemDialog(QDialog):
    """Modal dialog for adding a new Time Mode tracker item."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Time Item")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self._name_edit = QLineEdit()
        layout.addWidget(self._name_edit)

        time_layout = QHBoxLayout()

        self._hours_spin = QSpinBox()
        self._hours_spin.setMinimum(0)
        self._hours_spin.setMaximum(23)
        time_layout.addWidget(QLabel("Hours:"))
        time_layout.addWidget(self._hours_spin)

        self._minutes_spin = QSpinBox()
        self._minutes_spin.setMinimum(0)
        self._minutes_spin.setMaximum(59)
        time_layout.addWidget(QLabel("Minutes:"))
        time_layout.addWidget(self._minutes_spin)

        self._seconds_spin = QSpinBox()
        self._seconds_spin.setMinimum(0)
        self._seconds_spin.setMaximum(59)
        time_layout.addWidget(QLabel("Seconds:"))
        time_layout.addWidget(self._seconds_spin)

        layout.addLayout(time_layout)

        layout.addWidget(QLabel("Type:"))
        self._category_group = QButtonGroup(self)
        self._radio_map: dict[QRadioButton, ItemCategory] = {}
        for cat in ItemCategory:
            _, emoji = CATEGORY_STYLE[cat]
            label = f"{emoji} {cat.value}".strip()
            radio = QRadioButton(label)
            self._category_group.addButton(radio)
            self._radio_map[radio] = cat
            layout.addWidget(radio)
            if cat == ItemCategory.OTHER:
                radio.setChecked(True)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        cancel_button = QPushButton("Cancel")
        add_button.clicked.connect(self._on_add)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(add_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def _on_add(self) -> None:
        if not self._name_edit.text().strip():
            self._error_label.setText("Name cannot be empty.")
            self._error_label.show()
            return
        total = (
            self._hours_spin.value() * 3600
            + self._minutes_spin.value() * 60
            + self._seconds_spin.value()
        )
        if total == 0:
            self._error_label.setText("Duration must be greater than zero.")
            self._error_label.show()
            return
        self._error_label.hide()
        self.accept()

    def _selected_category(self) -> ItemCategory:
        for radio, cat in self._radio_map.items():
            if radio.isChecked():
                return cat
        return ItemCategory.OTHER

    def get_item(self) -> TimeTrackerItem:
        """Return the validated TimeTrackerItem. Call only after Accepted."""
        total = (
            self._hours_spin.value() * 3600
            + self._minutes_spin.value() * 60
            + self._seconds_spin.value()
        )
        return TimeTrackerItem(
            name=self._name_edit.text().strip(),
            seconds=total,
            category=self._selected_category(),
        )
