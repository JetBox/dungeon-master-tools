from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class ProjectDialog(QDialog):
    """Modal dialog for entering a new project name."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Project name:"))

        self._name_edit = QLineEdit()
        layout.addWidget(self._name_edit)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_ok(self) -> None:
        if not self._name_edit.text().strip():
            self._error_label.setText("Project name cannot be empty.")
            self._error_label.show()
        else:
            self._error_label.hide()
            self.accept()

    def get_name(self) -> str:
        """Return the entered project name."""
        return self._name_edit.text().strip()
