#!/usr/bin/env python3
# main.py - Alt KDE Helper (точка входа)

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from config import STYLESHEET
from gui import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Alt KDE Helper")
    app.setStyleSheet(STYLESHEET)

    # Устанавливаем иконку приложения
    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alt-kde-helper.svg")))

    # Устанавливаем desktop файл для идентификации в KDE/Wayland
    app.setDesktopFileName('alt-kde-helper')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
