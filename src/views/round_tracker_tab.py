import os
from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QCheckBox,
    QLabel,
    QSpinBox,
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

from src.models import RoundTrackerItem, TimeTrackerItem, ItemCategory, RoundTrackerState, TurnModeSettings, TimeModeSettings
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

    def get_state(self) -> RoundTrackerState:
        turn = self._turn_panel.get_state()
        time = self._time_panel.get_state()
        return RoundTrackerState(
            turn_items=[
                RoundTrackerItem(name=i["name"], rounds=i["rounds"], category=ItemCategory(i["category"]))
                for i in turn["items"]
            ],
            time_items=[
                TimeTrackerItem(name=i["name"], seconds=i["seconds"], category=ItemCategory(i["category"]))
                for i in time["items"]
            ],
            turn_settings=TurnModeSettings(
                re_interval=turn["settings"]["re_interval"],
                re_current=turn["settings"]["re_current"],
                time_per_turn=turn["settings"]["time_per_turn"],
                integrate_calendar=turn["settings"]["integrate_calendar"],
                sound_effects=turn["settings"]["sound_effects"],
            ),
            time_settings=TimeModeSettings(
                re_interval=time["settings"]["re_interval"],
                re_current_seconds=time["settings"]["re_current_seconds"],
                combat_round_seconds=time["settings"]["combat_round_seconds"],
                dungeon_round_minutes=time["settings"]["dungeon_round_minutes"],
                integrate_calendar=time["settings"]["integrate_calendar"],
                sound_effects=time["settings"]["sound_effects"],
            ),
        )

    def load_state(self, state: RoundTrackerState) -> None:
        self._turn_panel.load_state({
            "items": [{"name": item.name, "rounds": item.rounds, "category": item.category.value} for item in state.turn_items],
            "settings": {
                "re_interval": state.turn_settings.re_interval,
                "re_current": state.turn_settings.re_current,
                "time_per_turn": state.turn_settings.time_per_turn,
                "integrate_calendar": state.turn_settings.integrate_calendar,
                "sound_effects": state.turn_settings.sound_effects,
            },
        })
        self._time_panel.load_state({
            "items": [{"name": item.name, "seconds": item.seconds, "category": item.category.value} for item in state.time_items],
            "settings": {
                "re_interval": state.time_settings.re_interval,
                "re_current_seconds": state.time_settings.re_current_seconds,
                "combat_round_seconds": state.time_settings.combat_round_seconds,
                "dungeon_round_minutes": state.time_settings.dungeon_round_minutes,
                "integrate_calendar": state.time_settings.integrate_calendar,
                "sound_effects": state.time_settings.sound_effects,
            },
        })

    def clear(self) -> None:
        self._turn_panel.clear()
        self._time_panel.clear()


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

        # RE interval row
        re_row = QHBoxLayout()
        re_row.addWidget(QLabel("RE Interval:"))
        self._re_interval_spin = QSpinBox()
        self._re_interval_spin.setMinimum(0)
        self._re_interval_spin.setValue(2)
        self._re_interval_spin.valueChanged.connect(self._on_re_interval_changed)
        re_row.addWidget(self._re_interval_spin)
        sidebar.addLayout(re_row)

        # Time per turn row
        tpt_row = QHBoxLayout()
        tpt_row.addWidget(QLabel("Time/Turn (min):"))
        self._time_per_turn_spin = QSpinBox()
        self._time_per_turn_spin.setMinimum(1)
        self._time_per_turn_spin.setMaximum(600)
        self._time_per_turn_spin.setValue(6)
        tpt_row.addWidget(self._time_per_turn_spin)
        sidebar.addLayout(tpt_row)

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

    def _on_re_interval_changed(self, value: int) -> None:
        self._re_widget.set_interval(value)
        if value == 0:
            self._re_widget.hide()
        else:
            self._re_widget.show()

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
            self._calendar_advance(self._time_per_turn_spin.value() * 60)

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

    def get_state(self) -> dict:
        items = []
        for i in range(self._inner_layout.count()):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, ItemWidget):
                items.append({
                    "name": w._name_edit.text(),
                    "rounds": w.get_rounds(),
                    "category": w.get_category().value,
                })
        return {
            "items": items,
            "settings": {
                "re_interval": self._re_interval_spin.value(),
                "re_current": self._re_widget.get_current_value(),
                "time_per_turn": self._time_per_turn_spin.value(),
                "integrate_calendar": self._integrate_checkbox.isChecked(),
                "sound_effects": self._sound_checkbox.isChecked(),
            },
        }

    def load_state(self, state: dict) -> None:
        self.clear()
        s = state.get("settings", {})
        interval = s.get("re_interval", 2)
        current = s.get("re_current", interval)
        self._re_interval_spin.setValue(interval)
        self._re_widget.restore(interval, current)
        if interval == 0:
            self._re_widget.hide()
        else:
            self._re_widget.show()
        self._time_per_turn_spin.setValue(s.get("time_per_turn", 6))
        self._integrate_checkbox.setChecked(s.get("integrate_calendar", True))
        self._sound_checkbox.setChecked(s.get("sound_effects", True))
        for item_data in state.get("items", []):
            category = ItemCategory(item_data["category"])
            item = RoundTrackerItem(
                name=item_data["name"],
                rounds=item_data["rounds"],
                category=category,
            )
            widget = ItemWidget(item)
            widget.delete_requested.connect(self._on_delete_item)
            self._inner_layout.insertWidget(self._inner_layout.count() - 2, widget)

    def clear(self) -> None:
        for i in reversed(range(self._inner_layout.count())):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, ItemWidget):
                self._inner_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
        self._re_interval_spin.setValue(2)
        self._time_per_turn_spin.setValue(6)
        self._integrate_checkbox.setChecked(True)
        self._sound_checkbox.setChecked(True)
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

        # RE interval row (minutes)
        re_row = QHBoxLayout()
        re_row.addWidget(QLabel("RE Interval (min):"))
        self._re_interval_spin = QSpinBox()
        self._re_interval_spin.setMinimum(0)
        self._re_interval_spin.setMaximum(60)
        self._re_interval_spin.setValue(12)
        self._re_interval_spin.valueChanged.connect(self._on_re_interval_changed)
        re_row.addWidget(self._re_interval_spin)
        sidebar.addLayout(re_row)

        # Combat round duration (seconds)
        combat_row = QHBoxLayout()
        combat_row.addWidget(QLabel("Combat Round (sec):"))
        self._combat_spin = QSpinBox()
        self._combat_spin.setMinimum(1)
        self._combat_spin.setMaximum(3600)
        self._combat_spin.setValue(10)
        combat_row.addWidget(self._combat_spin)
        sidebar.addLayout(combat_row)

        # Dungeon round duration (minutes)
        dungeon_row = QHBoxLayout()
        dungeon_row.addWidget(QLabel("Dungeon Round (min):"))
        self._dungeon_spin = QSpinBox()
        self._dungeon_spin.setMinimum(1)
        self._dungeon_spin.setMaximum(600)
        self._dungeon_spin.setValue(6)
        dungeon_row.addWidget(self._dungeon_spin)
        sidebar.addLayout(dungeon_row)

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

    def _on_re_interval_changed(self, value: int) -> None:
        self._re_widget.set_interval(value)
        if value == 0:
            self._re_widget.hide()
        else:
            self._re_widget.show()

    def _on_combat_round(self) -> None:
        seconds = self._combat_spin.value()
        self._decrement_all(seconds)
        if self._integrate_checkbox.isChecked() and self._calendar_advance:
            self._calendar_advance(seconds)

    def _on_dungeon_round(self) -> None:
        seconds = self._dungeon_spin.value() * 60
        self._decrement_all(seconds)
        if self._integrate_checkbox.isChecked() and self._calendar_advance:
            self._calendar_advance(seconds)

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
        self.clear()

    def get_state(self) -> dict:
        items = []
        for i in range(self._inner_layout.count()):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, TimeItemWidget):
                items.append({
                    "name": w._name_edit.text(),
                    "seconds": w.get_seconds(),
                    "category": w.get_category().value,
                })
        return {
            "items": items,
            "settings": {
                "re_interval": self._re_interval_spin.value(),
                "re_current_seconds": self._re_widget.get_current_seconds(),
                "combat_round_seconds": self._combat_spin.value(),
                "dungeon_round_minutes": self._dungeon_spin.value(),
                "integrate_calendar": self._integrate_checkbox.isChecked(),
                "sound_effects": self._sound_checkbox.isChecked(),
            },
        }

    def load_state(self, state: dict) -> None:
        self.clear()
        s = state.get("settings", {})
        interval = s.get("re_interval", 12)
        current_seconds = s.get("re_current_seconds", interval * 60)
        self._re_interval_spin.setValue(interval)
        self._re_widget.restore(interval, current_seconds)
        if interval == 0:
            self._re_widget.hide()
        else:
            self._re_widget.show()
        self._combat_spin.setValue(s.get("combat_round_seconds", 10))
        self._dungeon_spin.setValue(s.get("dungeon_round_minutes", 6))
        self._integrate_checkbox.setChecked(s.get("integrate_calendar", True))
        self._sound_checkbox.setChecked(s.get("sound_effects", True))
        for item_data in state.get("items", []):
            category = ItemCategory(item_data["category"])
            item = TimeTrackerItem(
                name=item_data["name"],
                seconds=item_data["seconds"],
                category=category,
            )
            widget = TimeItemWidget(item)
            widget.delete_requested.connect(self._on_delete_item)
            self._inner_layout.insertWidget(self._inner_layout.count() - 2, widget)

    def clear(self) -> None:
        for i in reversed(range(self._inner_layout.count())):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, TimeItemWidget):
                self._inner_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
        self._re_interval_spin.setValue(12)
        self._combat_spin.setValue(10)
        self._dungeon_spin.setValue(6)
        self._integrate_checkbox.setChecked(True)
        self._sound_checkbox.setChecked(True)
        self._re_widget.reset()
