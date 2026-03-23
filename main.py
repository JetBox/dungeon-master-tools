import sys
from PyQt6.QtWidgets import QApplication

from src.serializer import Serializer
from src.views.main_window import MainWindow
from src.controller import AppController


def main() -> None:
    app = QApplication(sys.argv)
    serializer = Serializer()
    window = MainWindow()
    controller = AppController(window, serializer)  # noqa: F841 — must be kept alive
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
