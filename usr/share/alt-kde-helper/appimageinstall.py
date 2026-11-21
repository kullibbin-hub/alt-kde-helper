# appimageinstall.py - страница установки AppImage-приложений (шлюз к AM-GUI)
import os
import subprocess
import threading
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon
from config import get_scripts_dir
from busy import BUSY


class AppImageInstallPage(QWidget):
    _refresh_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 40, 30, 40)

        # Кнопка справки в правом верхнем углу
        help_layout = QHBoxLayout()
        help_layout.addStretch()
        self.btn_help = QPushButton("?")
        self.btn_help.setFixedSize(32, 32)
        self.btn_help.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.btn_help.setToolTip("Справка по установке AppImage")
        self.btn_help.clicked.connect(self._show_help)
        help_layout.addWidget(self.btn_help)
        layout.addLayout(help_layout)

        layout.addStretch()

        self.info_label = QLabel(
            "<b>Управление AppImage-приложениями</b><br><br>"
            "Теперь осуществляется через централизованный магазин <b>AM-GUI</b>.<br>"
            "Он автоматически управляет загрузкой, обновлением и интеграцией приложений."
        )
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        layout.addSpacing(40)

        self.btn_open_amgui = QPushButton("Открыть магазин appimage-приложений AM-GUI")
        self.btn_open_amgui.setProperty("class", "BottomButton")
        self.btn_open_amgui.setMinimumHeight(50)
        self.btn_open_amgui.setIcon(QIcon.fromTheme("system-software-install"))
        self.btn_open_amgui.clicked.connect(self._handle_open_amgui)
        layout.addWidget(self.btn_open_amgui)

        self.btn_extra_packages = QPushButton("Открыть дополнительный каталог пакетов для AM-GUI")
        self.btn_extra_packages.setProperty("class", "BottomButton")
        self.btn_extra_packages.setMinimumHeight(50)
        self.btn_extra_packages.setIcon(QIcon.fromTheme("globe"))
        self.btn_extra_packages.clicked.connect(self._open_extra_packages)
        layout.addWidget(self.btn_extra_packages)

        layout.addSpacing(60)

        # Блок удаления
        uninstall_layout = QHBoxLayout()
        uninstall_label = QLabel("Если магазин AM-GUI больше не нужен, его можно удалить.")
        uninstall_label.setWordWrap(True)
        uninstall_layout.addWidget(uninstall_label, 1)

        self.btn_uninstall = QPushButton("Удалить AM-GUI")
        self.btn_uninstall.setProperty("class", "BottomButton")
        self.btn_uninstall.setMinimumHeight(40)
        self.btn_uninstall.setIcon(QIcon.fromTheme("edit-delete"))
        self.btn_uninstall.clicked.connect(self._handle_uninstall)
        uninstall_layout.addWidget(self.btn_uninstall)

        layout.addLayout(uninstall_layout)

        layout.addStretch()
        self.setLayout(layout)

        self._amgui_path = ""
        self._refresh_signal.connect(self._check_amgui)

    def showEvent(self, event):
        super().showEvent(event)
        self._check_amgui()

    def _check_amgui(self):
        """Проверяет наличие AM-GUI в системе"""
        self._amgui_path = os.path.expanduser("~/bin/am-gui.AppImage")
        has_amgui = os.path.exists(self._amgui_path) and os.path.isfile(self._amgui_path)
        self.btn_extra_packages.setEnabled(has_amgui)
        self.btn_uninstall.setEnabled(has_amgui)

        if not has_amgui:
            self._show_help()

    def _handle_open_amgui(self):
        if not os.path.exists(self._amgui_path):
            res = subprocess.run([
                'kdialog', '--yesno',
                'AM-GUI не установлен.\nУстановить его сейчас?'
            ])
            if res.returncode == 0:
                self._install_amgui()
            return

        subprocess.Popen([self._amgui_path])

    def _open_extra_packages(self):
        if os.path.exists(self._amgui_path):
            self._link_appman()
            QDesktopServices.openUrl(QUrl("https://portable-linux-apps.github.io/en/apps.html"))

    def _link_appman(self):
        """Создаёт симлинк ~/bin/appman → ~/.local/bin/appman."""
        src = os.path.expanduser('~/.local/bin/appman')
        dst = os.path.expanduser('~/bin/appman')
        if not os.path.isfile(src):
            return
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.islink(dst):
                os.unlink(dst)
            os.symlink(src, dst)
        except Exception:
            pass

    def _handle_uninstall(self):
        if not os.path.exists(self._amgui_path):
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить AM-GUI?\n\n"
            "Будут удалены:\n"
            "• Исполняемый файл ~/bin/am-gui.AppImage\n"
            "• Ярлыки из меню приложений\n"
            "• Иконки и mime-типы",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        if BUSY.is_busy():
            return

        script = os.path.join(get_scripts_dir(), 'uninstall_am_gui.sh')
        if not os.path.exists(script):
            QMessageBox.critical(self, "Ошибка", f"Скрипт удаления не найден:\n{script}")
            return

        BUSY.acquire()
        cmd = f'bash "{script}"'
        self.process = subprocess.Popen(
            ['konsole', '--separate', '--title', 'Удаление AM-GUI', '-e', 'bash', '-c', cmd]
        )

        def wait_and_refresh():
            self.process.wait()
            BUSY.release()
            import time
            time.sleep(1)
            self._refresh_signal.emit()

        threading.Thread(target=wait_and_refresh, daemon=True).start()

    def _show_help(self):
        from PyQt6.QtWidgets import QDialog, QScrollArea, QFrame

        dialog = QDialog(self)
        dialog.setWindowTitle("Справка - Установка AppImage")
        dialog.setMinimumSize(600, 500)

        dlg_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        label = QLabel()
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        label.setContentsMargins(10, 10, 10, 10)

        help_text = """
<p><b>Открыть магазин appimage-приложений AM-GUI</b> — запуск магазина. При первом нажатии программа проверит, установлен ли он, и при необходимости предложит установить. Установка выполняется в отдельном окне терминала.</p>
<p><b>Важно при первой установке магазина:</b><br>
1. В процессе установки появится небольшое окно с вопросом о включении автоматических обновлений (update) — выберите <b>Да (Yes)</b>.<br>
2. Затем откроется выбор типа установки (два квадратных окна) — выберите вариант с надписью <b>"Quick install"</b>.</p>
<p><b>Открыть дополнительный каталог пакетов для AM-GUI</b> — открывает в браузере страницу с дополнительным списком приложений, доступных для установки через магазин. Кнопка активна только если магазин уже установлен.</p>
<p><b>Установка из дополнительного каталога:</b><br>
При нажатии на ссылку установки в браузере появится окно с запросом на открытие внешнего приложения — согласитесь. Откроется терминал, а затем появится выбор типа установки:<br>
• <b>user</b> — установка только для текущего пользователя (рекомендуется).<br>
• <b>system</b> — установка для всех пользователей системы (потребуется ввод пароля).</p>
<p><b>Удалить AM-GUI</b> — полностью удаляет магазин: исполняемый файл, ярлык из меню приложений, иконки и зарегистрированные типы файлов. Действие выполняется в отдельном окне терминала, требуется подтверждение.</p>
"""

        label.setText(help_text)
        scroll.setWidget(label)
        dlg_layout.addWidget(scroll)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        dlg_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        dialog.setLayout(dlg_layout)
        dialog.exec()

    def _install_amgui(self):
        if BUSY.is_busy():
            return

        script = os.path.join(get_scripts_dir(), 'install_am_gui.sh')
        if not os.path.exists(script):
            QMessageBox.critical(self, "Ошибка", f"Скрипт установки не найден:\n{script}")
            return

        BUSY.acquire()
        cmd = f'bash "{script}"'
        self.process = subprocess.Popen(
            ['konsole', '--separate', '--title', 'Установка AM-GUI', '-e', 'bash', '-c', cmd]
        )

        def wait_and_refresh():
            self.process.wait()
            BUSY.release()
            import time
            time.sleep(1.5)
            self._refresh_signal.emit()

        threading.Thread(target=wait_and_refresh, daemon=True).start()
