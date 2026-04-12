from PyQt6.QtWidgets import (
    QMainWindow, QMenuBar, QMenu, QTabWidget, QWidget,
    QStackedWidget, QVBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from src.views.round_tracker_tab import RoundTrackerTab
from src.views.calendar_tab import CalendarTab
from src.views.random_tables_tab import RandomTablesTab


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
        self.save_project_action.setShortcut(QKeySequence.StandardKey.Save)
        self.load_project_action = QAction("Load Project", self)

        file_menu.addAction(self.new_project_action)
        file_menu.addAction(self.save_project_action)
        file_menu.addAction(self.load_project_action)

        # Central tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(QWidget(), "Campaign Overview")
        self._round_tracker_tab = RoundTrackerTab()
        self._tab_widget.addTab(self._round_tracker_tab, "Round Tracker")
        self._calendar_tab = CalendarTab()
        self._tab_widget.addTab(self._calendar_tab, "Calendar")
        self._random_tables_tab = RandomTablesTab()
        self._tab_widget.addTab(self._random_tables_tab, "Random Tables")
        self.setCentralWidget(self._tab_widget)
        self._round_tracker_tab.set_calendar_advance(self._calendar_tab.advance_time)

        self._calendar_tab.calendar_selection_cancelled.connect(
            lambda: self._tab_widget.setCurrentIndex(0)
        )

        # No-project landing page (index 0 of stacked widget)
        _landing = QWidget()
        _landing_layout = QVBoxLayout(_landing)
        _landing_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        _prompt_label = QLabel("Create or Load a project to get started.")
        _prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _landing_layout.addWidget(_prompt_label)

        self.landing_new_project_btn = QPushButton("Create New Project")
        _landing_layout.addWidget(self.landing_new_project_btn)

        self.landing_load_project_btn = QPushButton("Load Project")
        _landing_layout.addWidget(self.landing_load_project_btn)

        # Stacked widget: index 0 = landing, index 1 = tab widget
        self._stacked_widget = QStackedWidget()
        self._stacked_widget.addWidget(_landing)
        self._stacked_widget.addWidget(self._tab_widget)
        self._stacked_widget.setCurrentIndex(0)

        self.setCentralWidget(self._stacked_widget)

    @property
    def calendar_tab(self) -> CalendarTab:
        """Return the CalendarTab instance."""
        return self._calendar_tab

    def set_title(self, project_name: str) -> None:
        """Update the window title to reflect the active project name."""
        self.setWindowTitle(project_name)

    def show_project(self, name: str) -> None:
        """Switch to the project view and update the title."""
        self._stacked_widget.setCurrentIndex(1)
        self.set_title(name)

    def show_no_project(self) -> None:
        """Switch to the no-project landing screen and reset the title."""
        self._stacked_widget.setCurrentIndex(0)
        self.setWindowTitle("TTRPG DM Tool")

    def reset_tab_state(self) -> None:
        """Clear transient tab state ready for a fresh project load."""
        self._round_tracker_tab.clear()
        self._tab_widget.setCurrentIndex(0)
        if hasattr(self._calendar_tab, "reset"):
            self._calendar_tab.reset()
