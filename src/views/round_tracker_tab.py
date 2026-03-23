from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QSpacerItem,
    QSizePolicy,
)

from src.views.add_item_dialog import AddItemDialog
from src.views.item_widget import ItemWidget


class RoundTrackerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        add_button = QPushButton("Add Item")
        add_button.clicked.connect(self._on_add_item)
        layout.addWidget(add_button)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)

        self._inner_widget = QWidget()
        self._inner_layout = QVBoxLayout(self._inner_widget)
        self._spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._inner_layout.addSpacerItem(self._spacer)

        self._scroll_area.setWidget(self._inner_widget)
        layout.addWidget(self._scroll_area)

    def _on_add_item(self) -> None:
        """Open AddItemDialog; on accept, append ItemWidget to scroll area."""
        dialog = AddItemDialog(self)
        if dialog.exec() == AddItemDialog.DialogCode.Accepted:
            item = dialog.get_item()
            widget = ItemWidget(item)
            # Insert before the spacer (last item in layout)
            self._inner_layout.insertWidget(self._inner_layout.count() - 1, widget)
