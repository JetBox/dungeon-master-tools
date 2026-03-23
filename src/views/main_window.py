from PyQt6.QtWidgets import QMainWindow, QMenuBar, QMenu, QTabWidget, QWidget
from PyQt6.QtGui import QAction
from src.views.round_tracker_tab import RoundTrackerTab


class MainWindow(QMainWindow):
    """Top-level application window with menu bar and tabbed interface."""

    def __init__(self) -> None:
        super().__init__()

        # Window sizing
        self.resize(1024, 768)
        self.setMinimumSize(640, 480)

        # Menu bar
        menu_bar: QMenuBar = self.menuBar()
        file_menu: QMenu = menu_bar.addMenu("File")

        self.new_project_action = QAction("New Project", self)
        self.save_project_action = QAction("Save Project", self)
        self.load_project_action = QAction("Load Project", self)

        file_menu.addAction(self.new_project_action)
        file_menu.addAction(self.save_project_action)
        file_menu.addAction(self.load_project_action)

        # Central tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(QWidget(), "Campaign Overview")
        self._round_tracker_tab = RoundTrackerTab()
        self._tab_widget.addTab(self._round_tracker_tab, "Round Tracker")
        self.setCentralWidget(self._tab_widget)

    def set_title(self, project_name: str) -> None:
        """Update the window title to reflect the active project name."""
        self.setWindowTitle(project_name)
