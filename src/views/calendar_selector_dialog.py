import os

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.calendar_loader import load_calendar_file
from src.errors import ProjectLoadError
from src.models import CalendarDefinition, FantasyDateTime

_GREGORIAN_JSON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "calendars", "gregorian.json")
)


class CalendarSelectorDialog(QDialog):
    """Modal dialog for choosing a calendar definition for a new project."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose Calendar")
        self._calendar: CalendarDefinition | None = None
        self._initial_date: FantasyDateTime | None = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Choose a calendar for this project:"))

        gregorian_btn = QPushButton("Use Gregorian (Default)")
        gregorian_btn.clicked.connect(self._on_use_gregorian)
        layout.addWidget(gregorian_btn)

        load_btn = QPushButton("Load from File")
        load_btn.clicked.connect(self._on_load_from_file)
        layout.addWidget(load_btn)

        fantasy_btn = QPushButton("Create Your Own")
        fantasy_btn.clicked.connect(self._on_generate_fantasy)
        layout.addWidget(fantasy_btn)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_use_gregorian(self) -> None:
        try:
            self._calendar = load_calendar_file(_GREGORIAN_JSON)
            self._error_label.hide()
            self.accept()
        except ProjectLoadError as e:
            self._error_label.setText(str(e))
            self._error_label.show()

    def _on_load_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Calendar File", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            self._calendar = load_calendar_file(path)
            self._error_label.hide()
            self.accept()
        except ProjectLoadError as e:
            self._error_label.setText(str(e))
            self._error_label.show()

    def _on_generate_fantasy(self) -> None:
        from src.views.calendar_wizard_dialog import CalendarWizardDialog
        wizard = CalendarWizardDialog(self)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            self._calendar = wizard.get_calendar()
            self._initial_date = wizard.get_initial_date()
            self.accept()

    def get_calendar(self) -> CalendarDefinition | None:
        """Return the chosen CalendarDefinition, or None if cancelled."""
        return self._calendar

    def get_initial_date(self) -> FantasyDateTime | None:
        """Return the initial FantasyDateTime from the wizard, or None."""
        return self._initial_date
