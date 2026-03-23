import os

from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

from src.views.add_item_dialog import AddItemDialog
from src.views.item_widget import ItemWidget
from src.views.random_encounter_widget import RandomEncounterWidget

_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio")
_BEEP_PATH = os.path.join(_AUDIO_DIR, "notif_end.mp3")
_RE_BEEP_PATH = os.path.join(_AUDIO_DIR, "notif_random_encounter.mp3")


class RoundTrackerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Root layout: sidebar on the left, scroll area on the right
        root = QHBoxLayout(self)

        # --- Sidebar ---
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(4, 4, 4, 4)

        next_round_button = QPushButton("Next Round")
        next_round_button.setFixedHeight(48)
        next_round_button.clicked.connect(self._on_next_round)
        sidebar.addWidget(next_round_button)

        # Horizontal separator line
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

        # Random encounter widget always pinned at index 0
        self._re_widget = RandomEncounterWidget()
        self._inner_layout.addWidget(self._re_widget)

        # "+" add button pinned above the spacer
        self._add_inline_btn = QPushButton("+")
        self._add_inline_btn.setFixedHeight(40)
        self._add_inline_btn.clicked.connect(self._on_add_item)
        self._inner_layout.addWidget(self._add_inline_btn)

        self._spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._inner_layout.addSpacerItem(self._spacer)

        self._scroll_area.setWidget(self._inner_widget)
        root.addWidget(self._scroll_area)

    # ------------------------------------------------------------------

    def _on_clear(self) -> None:
        """Remove all ItemWidgets; reset the Random Encounter widget."""
        for i in reversed(range(self._inner_layout.count())):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, ItemWidget):
                self._inner_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
        self._re_widget.reset()

    def _on_next_round(self) -> None:
        """Decrement all widgets; play appropriate sounds for any that hit 0."""
        hit_zero = False
        for i in range(self._inner_layout.count()):
            widget = self._inner_layout.itemAt(i).widget()
            if isinstance(widget, ItemWidget):
                if widget.decrement():
                    hit_zero = True

        # Handle random encounter widget separately
        if self._re_widget.isVisible() and self._re_widget.decrement():
            self._re_sound.stop()
            self._re_sound.play()
            self._re_widget.reset()

        if hit_zero:
            self._sound.stop()
            self._sound.play()

    def _on_add_item(self) -> None:
        """Open AddItemDialog; on accept, append ItemWidget to scroll area."""
        dialog = AddItemDialog(self)
        if dialog.exec() == AddItemDialog.DialogCode.Accepted:
            item = dialog.get_item()
            widget = ItemWidget(item)
            widget.delete_requested.connect(self._on_delete_item)
            # Insert before the + button and spacer (last two items)
            self._inner_layout.insertWidget(self._inner_layout.count() - 2, widget)

    def _on_delete_item(self, widget: ItemWidget) -> None:
        self._inner_layout.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()

    def _on_sort(self) -> None:
        """Stable-sort all ItemWidgets by round count; RE widget stays pinned at top."""
        widgets = []
        for i in range(self._inner_layout.count()):
            w = self._inner_layout.itemAt(i).widget()
            if isinstance(w, ItemWidget):
                widgets.append(w)

        for w in widgets:
            self._inner_layout.removeWidget(w)

        for w in sorted(widgets, key=lambda w: w.get_rounds()):
            self._inner_layout.insertWidget(self._inner_layout.count() - 1, w)
