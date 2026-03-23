from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.errors import ProjectLoadError
from src.models import Project
from src.serializer import Serializer
from src.views.main_window import MainWindow
from src.views.project_dialog import ProjectDialog


class AppController:
    """Coordinates between the view and model; owns the active Project."""

    def __init__(self, window: MainWindow, serializer: Serializer) -> None:
        self._window = window
        self._serializer = serializer
        self._project: Project | None = None

        window.new_project_action.triggered.connect(self.on_new_project)
        window.save_project_action.triggered.connect(self.on_save_project)
        window.load_project_action.triggered.connect(self.on_load_project)

    def on_new_project(self) -> None:
        dialog = ProjectDialog(self._window)
        if dialog.exec() == ProjectDialog.DialogCode.Accepted:
            self._project = Project(name=dialog.get_name())
            self._window.set_title(self._project.name)

    def on_save_project(self) -> None:
        if self._project is None:
            QMessageBox.information(self._window, "Save Project", "No project to save.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self._window,
            "Save Project",
            "",
            "JSON Files (*.json)",
        )
        if not path:
            return

        try:
            self._serializer.save(self._project, path)
        except OSError as e:
            QMessageBox.critical(self._window, "Save Error", str(e))

    def on_load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self._window,
            "Load Project",
            "",
            "JSON Files (*.json)",
        )
        if not path:
            return

        try:
            project = self._serializer.load(path)
        except ProjectLoadError as e:
            QMessageBox.critical(self._window, "Load Error", str(e))
            return
        except OSError as e:
            QMessageBox.critical(self._window, "Load Error", str(e))
            return

        self._project = project
        self._window.set_title(self._project.name)
