import os
from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QCheckBox,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QTabBar,
    QStackedWidget,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

from src.views.add_item_dialog import AddItemDialog
from src.views.add_time_item_dialog import AddTimeItemDialog
from src.views.item_widget import ItemWidget
from src.views.random_encounter_widget import RandomEncounterWidget
from src.views.time_item_widget import TimeItemWidget
from src.views.time_random_encounter_widget import TimeRandomEncounterWidget

_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio")
_BEEP_PATH = os.path.join(_AUDIO_DIR, "notif_end.mp3")
_RE_BEEP_PATH = os.path.join(_AUDIO_DIR, "notif_random_encounter.mp3")


class RoundTrackerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        tab_bar = QTabBar()
        tab_bar.addTab("Turn Mode")
        tab_bar.addTab("Time Mode")
        layout.addWidget(tab_bar)

        self._turn_panel = TurnModePanel()
        self._time_panel = TimeModePanel()

        stacked = QStackedWidget()
        stacked.addWidget(self._turn_panel)
        stacked.addWidget(self._time_panel)
        layout.addWidget(stacked)

        tab_bar.currentChanged.connect(stacked.setCurrentIndex)

    def set_calendar_advance(self, fn: Callable[[int], None]) -> None:
        self._turn_panel.set_calendar_advance(fn)
        self._time_panel.set_calendar_advance(fn)


class TurnModePanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._calendar_advance: Optional[Callable[[int], None]] = None

        root = QHBoxLayout(self)

        # --- Sidebar ---
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(4, 4, 4, 4)

        next_round_button = QPushButton("Next Round")
        next_round_button.setFixedHeight(48)
        next_round_button.clicked.connect(self._on_next_round)
        sidebar.addWidget(next_round_button)

        separator = QWidget()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: palette(mid);")
        sidebar.addWidget(separator)

        add_button = QPushButton("Add Item")
        add_button.clicked.connect(self._on_add_item)
        sidebar.addWidget(add_button)

        sort_button = QPushButton("Sort")
        sort_button.clicked.connect(self._on_sort)
        sidebar.addWidget(sort_button)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._on_clear)
        sidebar.addWidget(clear_button)

        self._integrate_checkbox = QCheckBox("Integrate with Calendar")
        self._integrate_checkbox.setChecked(True)
        sidebar.addWidget(self._integrate_checkbox)

        self._sound_checkbox = QCheckBox("Sound Effects")
        self._sound_checkbox.setChecked(True)
        sidebar.addWidget(self._sound_checkbox)

        sidebar.addStretch()
        root.addLayout(sidebar)

        # --- Sound effects ---
        self._audio_output = QAudioOutput()
        self._sound = QMediaPlayer()
        self._sound.setAudioOutput(self._audio_output)
        self._sound.setSource(QUrl.fromLocalFile(os.path.abspath(_BEEP_PATH)))

        self._re_audio_output = QAudioOutput()
        self._re_sound = QMediaPlayer()
        self._re_sound.setAudioOutput(self._re_audio_output)
        self._re_sound.setSource(QUrl.fromLocalFile(os.path.abspath(_RE_BEEP_PATH)))

        # --- Scroll area ---
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)

        self._inner_widget = QWidget()
        self._inner_layout = QVBoxLayout(self._inner_widget)

        self._re_widget = RandomEncounterWidget()
        self._inner_layout.addWidget(self._re_widget)

        self._add_inline_btn = QPushButton("+")
        self._add_inline_btn.setFixedHeight(40)
        self._add_inline_btn.clicked.connect(self._on_add_item)
        self._inner_layout.addWidget(self._add_inline_btn)

        self._spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._inner_layout.addSpacerItem(self._spacer)

        self._scroll_area.setWidget(self._inner_widget)
        root.addWidget(self._scroll_area)

    def set_calendar_advance(self, fn: Callable[[int], None]) -> None:
        self._calendar_advance = fn

    def _on_next_round(self) -> None:
        hit_zero = False
        for i in range(self._inner_layout.count()):
            widget = self._inner_layout.itemAt(i).widget()
            if isinstance(widget, ItemWidget):
                if widget.decrement():
                    hit_zero = True

        if self._re_widget.isVisible() and self._re_widget.decrement():
            if self._sound_checkbox.isChecked():
                self._re_sound.stop()
                self._re_sound.play()
            self._re_widget.reset()

        if hit_zero and self._sound_checkbox.isChecked():
            self._sound.stop()
            self._sound.play()

        if self._integrate_checkbox.isChecked() and self._calendar_advance:
            self._calendar_advance(360)  # Next Round = 6 minutes

    def _on_add_item(self) -> None:
        dialog = AddItemDialog(self)
        if dialog.exec() == AddItemDialog.DialogCode.Accepted:
            item = dialog.get_item()
            widget = ItemWidget(item)
            widget.delete_requested.connect(self._on_delete_item)
            self._inner_layout.insertWidget(self._inner_layout.count() - 2, widget)

    def _on_delete_item(self, widget: ItemWidget) -> None:
        self._inner_layout.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()

    def _on_sort(self) -> None:
        widgets = []
        for i in range(self._inner_layout.count()):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, ItemWidget):
                widgets.append(w)
        for w in widgets:
            self._inner_layout.removeWidget(w)
        for w in sorted(widgets, key=lambda w: w.get_rounds()):
            self._inner_layout.insertWidget(self._inner_layout.count() - 1, w)

    def _on_clear(self) -> None:
        for i in reversed(range(self._inner_layout.count())):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, ItemWidget):
                self._inner_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
        self._re_widget.reset()


class TimeModePanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._calendar_advance: Optional[Callable[[int], None]] = None

        root = QHBoxLayout(self)

        # --- Sidebar ---
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(4, 4, 4, 4)

        combat_round_button = QPushButton("Combat Round")
        combat_round_button.setFixedHeight(48)
        combat_round_button.clicked.connect(self._on_combat_round)
        sidebar.addWidget(combat_round_button)

        dungeon_round_button = QPushButton("Dungeon Round")
        dungeon_round_button.setFixedHeight(48)
        dungeon_round_button.clicked.connect(self._on_dungeon_round)
        sidebar.addWidget(dungeon_round_button)

        separator = QWidget()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: palette(mid);")
        sidebar.addWidget(separator)

        add_button = QPushButton("Add Item")
        add_button.clicked.connect(self._on_add_item)
        sidebar.addWidget(add_button)

        sort_button = QPushButton("Sort")
        sort_button.clicked.connect(self._on_sort)
        sidebar.addWidget(sort_button)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._on_clear)
        sidebar.addWidget(clear_button)

        self._integrate_checkbox = QCheckBox("Integrate with Calendar")
        self._integrate_checkbox.setChecked(True)
        sidebar.addWidget(self._integrate_checkbox)

        self._sound_checkbox = QCheckBox("Sound Effects")
        self._sound_checkbox.setChecked(True)
        sidebar.addWidget(self._sound_checkbox)

        sidebar.addStretch()
        root.addLayout(sidebar)

        # --- Sound effects ---
        self._audio_output = QAudioOutput()
        self._sound = QMediaPlayer()
        self._sound.setAudioOutput(self._audio_output)
        self._sound.setSource(QUrl.fromLocalFile(os.path.abspath(_BEEP_PATH)))

        self._re_audio_output = QAudioOutput()
        self._re_sound = QMediaPlayer()
        self._re_sound.setAudioOutput(self._re_audio_output)
        self._re_sound.setSource(QUrl.fromLocalFile(os.path.abspath(_RE_BEEP_PATH)))

        # --- Scroll area ---
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)

        self._inner_widget = QWidget()
        self._inner_layout = QVBoxLayout(self._inner_widget)

        self._re_widget = TimeRandomEncounterWidget()
        self._inner_layout.addWidget(self._re_widget)

        self._add_inline_btn = QPushButton("+")
        self._add_inline_btn.setFixedHeight(40)
        self._add_inline_btn.clicked.connect(self._on_add_item)
        self._inner_layout.addWidget(self._add_inline_btn)

        self._spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._inner_layout.addSpacerItem(self._spacer)

        self._scroll_area.setWidget(self._inner_widget)
        root.addWidget(self._scroll_area)

    def set_calendar_advance(self, fn: Callable[[int], None]) -> None:
        self._calendar_advance = fn

    def _on_combat_round(self) -> None:
        self._decrement_all(10)
        if self._integrate_checkbox.isChecked() and self._calendar_advance:
            self._calendar_advance(10)  # Combat Round = 10 seconds

    def _on_dungeon_round(self) -> None:
        self._decrement_all(360)
        if self._integrate_checkbox.isChecked() and self._calendar_advance:
            self._calendar_advance(360)  # Dungeon Round = 6 minutes

    def _decrement_all(self, seconds: int) -> None:
        hit_zero = False
        for i in range(self._inner_layout.count()):
            widget = self._inner_layout.itemAt(i).widget()
            if isinstance(widget, TimeItemWidget):
                if widget.decrement(seconds):
                    hit_zero = True

        if self._re_widget.isVisible() and self._re_widget.decrement(seconds):
            if self._sound_checkbox.isChecked():
                self._re_sound.stop()
                self._re_sound.play()

        if hit_zero and self._sound_checkbox.isChecked():
            self._sound.stop()
            self._sound.play()

    def _on_add_item(self) -> None:
        dialog = AddTimeItemDialog(self)
        if dialog.exec() == AddTimeItemDialog.DialogCode.Accepted:
            item = dialog.get_item()
            widget = TimeItemWidget(item)
            widget.delete_requested.connect(self._on_delete_item)
            self._inner_layout.insertWidget(self._inner_layout.count() - 2, widget)

    def _on_delete_item(self, widget: TimeItemWidget) -> None:
        self._inner_layout.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()

    def _on_sort(self) -> None:
        widgets = []
        for i in range(self._inner_layout.count()):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, TimeItemWidget):
                widgets.append(w)
        for w in widgets:
            self._inner_layout.removeWidget(w)
        for w in sorted(widgets, key=lambda w: w.get_seconds()):
            self._inner_layout.insertWidget(self._inner_layout.count() - 1, w)

    def _on_clear(self) -> None:
        for i in reversed(range(self._inner_layout.count())):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, TimeItemWidget):
                self._inner_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
        self._re_widget.reset()
