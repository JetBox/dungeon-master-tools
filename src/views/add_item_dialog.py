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

from src.models import RoundTrackerItem, ItemCategory, CATEGORY_STYLE


class AddItemDialog(QDialog):
    """Modal dialog for adding a new Round Tracker item."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Item")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self._name_edit = QLineEdit()
        layout.addWidget(self._name_edit)

        layout.addWidget(QLabel("Rounds:"))
        self._rounds_spin = QSpinBox()
        self._rounds_spin.setMinimum(1)
        layout.addWidget(self._rounds_spin)

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

    def _selected_category(self) -> ItemCategory:
        for radio, cat in self._radio_map.items():
            if radio.isChecked():
                return cat
        return ItemCategory.OTHER

    def _on_add(self) -> None:
        if not self._name_edit.text().strip():
            self._error_label.setText("Name cannot be empty.")
            self._error_label.show()
            return
        if self._rounds_spin.value() < 1:
            self._error_label.setText("Rounds must be at least 1.")
            self._error_label.show()
            return
        self._error_label.hide()
        self.accept()

    def get_item(self) -> RoundTrackerItem:
        """Return the validated RoundTrackerItem. Call only after Accepted."""
        return RoundTrackerItem(
            name=self._name_edit.text().strip(),
            rounds=self._rounds_spin.value(),
            category=self._selected_category(),
        )
