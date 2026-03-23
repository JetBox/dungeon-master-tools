from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from src.models import RoundTrackerItem


class ItemWidget(QFrame):
    def __init__(self, item: RoundTrackerItem, parent=None) -> None:
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.Box)

        layout = QHBoxLayout(self)

        name_label = QLabel(item.name)
        rounds_label = QLabel(str(item.rounds))
        rounds_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(name_label)
        layout.addWidget(rounds_label)
