#!/usr/bin/python3
# gui.py - графический интерфейс Alt KDE Helper
import sys
import os
import shutil
import subprocess
import glob
import signal
import tarfile
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QFrame,
    QScrollArea, QMessageBox, QPushButton, QButtonGroup, QDialog, QApplication,
    QMenu, QRadioButton, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QPoint, QEvent, QSize
from PyQt6.QtGui import QDesktopServices, QIcon, QCloseEvent, QAction, QPixmap
from config import (
    get_stylesheet, get_scripts_dir, get_state_dir, get_actions_dir,
    clear_actions_dir, get_help_path, get_version
)
from flatbackup import FlatpakBackupPage
from flatinstall import FlatpakInstallPage
from busy import BUSY

# Путь к вшитому пресету панели
PRESET_FILE_PATH = '/opt/alt-kde-helper/usr/share/alt-kde-helper/plasma-org.kde.plasma.desktop-appletsrc'
# Имя файла настроек панели KDE
PANEL_CONFIG_FILENAME = 'plasma-org.kde.plasma.desktop-appletsrc'

def get_current_version():
    """Возвращает текущую версию программы из version.txt"""
    with open('/usr/share/doc/alt-kde-helper/version.txt', 'r') as f:
        return f.read().strip()

def get_config_dir():
    """Возвращает путь к папке конфигурации программы"""
    return os.path.expanduser('~/.config/alt-kde-helper')

def get_packages_file_path():
    """Возвращает путь к файлу списка пакетов для текущей версии"""
    config_dir = get_config_dir()
    version = get_current_version()
    return os.path.join(config_dir, f'user_packages_{version}.txt')

def get_default_packages_path():
    """Возвращает путь к системному файлу со списком пакетов по умолчанию"""
    return '/opt/alt-kde-helper/usr/share/alt-kde-helper/default_packages.txt'

def ensure_packages_file(parent=None):
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)
    current_version = get_current_version()

    target_file = get_packages_file_path()
    default_file = get_default_packages_path()

    if os.path.exists(target_file):
        return target_file

    old_files = glob.glob(os.path.join(config_dir, 'user_packages_*.txt'))
    old_files = [f for f in old_files if not f.endswith('.old.txt')]

    if not old_files:
        if os.path.exists(default_file):
            shutil.copy2(default_file, target_file)
        else:
            open(target_file, 'w').close()
        return target_file

    old_files.sort()
    latest_old_file = old_files[-1]

    dialog = QDialog(parent) if parent else QDialog()
    dialog.setWindowTitle("Обновление списка пакетов")
    dialog.setMinimumWidth(550)

    layout = QVBoxLayout()
    title = QLabel(f"<b>Обнаружена новая версия программы ({current_version})</b>")
    title.setWordWrap(True)
    layout.addWidget(title)
    layout.addSpacing(10)

    info = QLabel("В новой версии изменён и дополнен список рекомендуемых пакетов.")
    info.setWordWrap(True)
    layout.addWidget(info)
    layout.addSpacing(15)

    keep_radio = QRadioButton("Оставить мой текущий список")
    keep_radio.setToolTip("Ваши личные изменения сохранятся, новые пакеты из обновления добавлены не будут")
    replace_radio = QRadioButton("Заменить список новым (рекомендуется)")
    replace_radio.setToolTip("Вы получите актуальный список пакетов для установки")
    replace_radio.setChecked(True)

    layout.addWidget(keep_radio)
    layout.addWidget(replace_radio)
    layout.addSpacing(15)

    folder_link = QLabel(
        f'📁 <b>Ваш старый список не будет удалён.</b><br>'
        f'Он останется в папке: <a href="file://{config_dir}">{config_dir}</a>'
    )
    folder_link.setWordWrap(True)
    folder_link.setOpenExternalLinks(True)
    layout.addWidget(folder_link)
    layout.addSpacing(20)

    button_layout = QHBoxLayout()
    ok_btn = QPushButton("Продолжить")
    cancel_btn = QPushButton("Отмена")
    button_layout.addStretch()
    button_layout.addWidget(ok_btn)
    button_layout.addWidget(cancel_btn)
    layout.addLayout(button_layout)

    dialog.setLayout(layout)

    def on_ok(): dialog.done(1)
    def on_cancel(): dialog.done(0)

    ok_btn.clicked.connect(on_ok)
    cancel_btn.clicked.connect(on_cancel)

    result = dialog.exec()

    if result == 0:
        return None

    if replace_radio.isChecked():
        if os.path.exists(default_file):
            shutil.copy2(default_file, target_file)
        else:
            open(target_file, 'w').close()
    else:
        shutil.copy2(latest_old_file, target_file)

    return target_file

def copy_and_patch(src, dst, actions_dir):
    """Копирует скрипт, заменяя жестко прописанный путь /tmp/alt-kde-helper-actions
    на актуальный путь для текущего пользователя."""
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()
    # Заменяем старый путь на новый
    content = content.replace('/tmp/alt-kde-helper-actions', actions_dir)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)
    os.chmod(dst, 0o755)

class ActionWorker(QThread):
    finished = pyqtSignal()

    def __init__(self, actions_dir):
        super().__init__()
        self.actions_dir = actions_dir
        self.process = None
        self.terminal_pid = None

    def run(self):
        scripts = sorted(glob.glob(os.path.join(self.actions_dir, '*.sh')))
        if not scripts:
            self.finished.emit()
            return

        cmd = 'for script in ' + ' '.join(f'"{s}"' for s in scripts) + '; do bash "$script"; done'

        BUSY.acquire()
        try:
            self.process = subprocess.Popen(
                ['konsole', '--separate', '--title', 'Применение изменений', '-e', 'bash', '-c', cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            import time
            time.sleep(0.5)

            try:
                result = subprocess.run(['pgrep', '-f', f'konsole.*Применение изменений'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    self.terminal_pid = int(result.stdout.strip().split('\n')[0])
            except:
                pass

            self.process.wait()
        finally:
            BUSY.release()
        self.finished.emit()

    def terminate_terminal(self):
        if self.terminal_pid:
            try:
                os.kill(self.terminal_pid, signal.SIGTERM)
            except:
                pass
        elif self.process and self.process.poll() is None:
            self.process.terminate()

class ActionCard(QFrame):
    def __init__(self, description, tooltip_text, script_name, rollback_script_name, parent=None):
        super().__init__(parent)
        self.script_name = script_name
        self.rollback_script_name = rollback_script_name
        self.setProperty("class", "ActionCard")

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 2, 12, 2)

        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setToolTip(tooltip_text)
        self.desc_label.setCursor(Qt.CursorShape.WhatsThisCursor)
        layout.addWidget(self.desc_label, 1)

        self.install_cb = QCheckBox("Применить")
        self.install_cb.setToolTip(tooltip_text)
        self.install_cb.stateChanged.connect(self.on_install_changed)
        layout.addWidget(self.install_cb)

        self.rollback_cb = QCheckBox("Откат")
        self.rollback_cb.setToolTip(f"Откатить: {description}")
        self.rollback_cb.stateChanged.connect(self.on_rollback_changed)
        layout.addWidget(self.rollback_cb)

        self.setLayout(layout)
        self.load_state()

    def load_state(self):
        state_dir = get_state_dir()
        state_file = os.path.join(state_dir, self.script_name)
        has_flag = os.path.exists(state_file)

        if has_flag:
            self.desc_label.setProperty("class", "DescriptionGreen")
            self.setProperty("class", "ActionCardGreen")
        else:
            if self.install_cb.isChecked():
                self.desc_label.setProperty("class", "DescriptionOrange")
                self.setProperty("class", "ActionCardOrange")
            else:
                self.desc_label.setProperty("class", "Description")
                self.setProperty("class", "ActionCard")

        self.style().unpolish(self)
        self.style().polish(self)
        self.desc_label.style().unpolish(self.desc_label)
        self.desc_label.style().polish(self.desc_label)
        self.rollback_cb.setEnabled(has_flag)

    def update_style(self, state_type):
        if state_type == 'orange':
            self.desc_label.setProperty("class", "DescriptionOrange")
            self.setProperty("class", "ActionCardOrange")
        elif state_type == 'green':
            self.desc_label.setProperty("class", "DescriptionGreen")
            self.setProperty("class", "ActionCardGreen")
        else:
            self.desc_label.setProperty("class", "Description")
            self.setProperty("class", "ActionCard")

        self.style().unpolish(self)
        self.style().polish(self)
        self.desc_label.style().unpolish(self.desc_label)
        self.desc_label.style().polish(self.desc_label)

    def on_install_changed(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        if is_checked:
            self.rollback_cb.blockSignals(True)
            self.rollback_cb.setChecked(False)
            self.rollback_cb.blockSignals(False)
            self.update_style('orange')
        else:
            state_dir = get_state_dir()
            state_file = os.path.join(state_dir, self.script_name)
            if os.path.exists(state_file):
                self.update_style('green')
            else:
                self.update_style('normal')

    def on_rollback_changed(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        if is_checked:
            self.install_cb.blockSignals(True)
            self.install_cb.setChecked(False)
            self.install_cb.blockSignals(False)
            self.update_style('orange')
        else:
            state_dir = get_state_dir()
            state_file = os.path.join(state_dir, self.script_name)
            if os.path.exists(state_file):
                self.update_style('green')
            else:
                self.update_style('normal')

class SimpleActionCard(QFrame):
    def __init__(self, description, tooltip_text, script_name, parent=None):
        super().__init__(parent)
        self.script_name = script_name
        self.setProperty("class", "SimpleActionCard")

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 2, 12, 2)

        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setToolTip(tooltip_text)
        self.desc_label.setCursor(Qt.CursorShape.WhatsThisCursor)
        layout.addWidget(self.desc_label, 1)

        self.install_cb = QCheckBox("Применить")
        self.install_cb.setToolTip(tooltip_text)
        self.install_cb.stateChanged.connect(self.on_install_changed)
        layout.addWidget(self.install_cb)

        self.setLayout(layout)
        self.load_state()

    def load_state(self):
        state_dir = get_state_dir()
        state_file = os.path.join(state_dir, self.script_name)
        has_flag = os.path.exists(state_file)

        if has_flag:
            self.desc_label.setProperty("class", "DescriptionGreen")
            self.setProperty("class", "SimpleActionCardGreen")
        else:
            if self.install_cb.isChecked():
                self.desc_label.setProperty("class", "DescriptionOrange")
                self.setProperty("class", "SimpleActionCardOrange")
            else:
                self.desc_label.setProperty("class", "Description")
                self.setProperty("class", "SimpleActionCard")

        self.style().unpolish(self)
        self.style().polish(self)
        self.desc_label.style().unpolish(self.desc_label)
        self.desc_label.style().polish(self.desc_label)

    def update_style(self, state_type):
        if state_type == 'orange':
            self.desc_label.setProperty("class", "DescriptionOrange")
            self.setProperty("class", "SimpleActionCardOrange")
        elif state_type == 'green':
            self.desc_label.setProperty("class", "DescriptionGreen")
            self.setProperty("class", "SimpleActionCardGreen")
        else:
            self.desc_label.setProperty("class", "Description")
            self.setProperty("class", "SimpleActionCard")

        self.style().unpolish(self)
        self.style().polish(self)
        self.desc_label.style().unpolish(self.desc_label)
        self.desc_label.style().polish(self.desc_label)

    def on_install_changed(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        if is_checked:
            self.update_style('orange')
        else:
            state_dir = get_state_dir()
            state_file = os.path.join(state_dir, self.script_name)
            if os.path.exists(state_file):
                self.update_style('green')
            else:
                self.update_style('normal')

class MirrorCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mirrors = [
            ("02_repo_fast_mirror_action.sh", "Подключить самое быстрое зеркало репозитория"),
            ("03_repo_yandex_action.sh", "Зеркало на Yandex"),
            ("04_repo_p11_action.sh", "Репозиторий по умолчанию"),
        ]

        self.radio_buttons = {}
        self.button_group = QButtonGroup()
        self.button_group.buttonToggled.connect(self.on_radio_toggled)

        self.frame = QFrame()
        self.frame.setProperty("class", "MirrorCard")

        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(12, 4, 12, 4)

        title = QLabel("Выбор зеркала репозитория")
        title.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        frame_layout.addWidget(title)

        none_widget = QWidget()
        none_layout = QHBoxLayout()
        none_layout.setContentsMargins(0, 2, 0, 2)
        none_label = QLabel("Не менять текущее зеркало")
        none_label.setWordWrap(True)
        none_layout.addWidget(none_label, 1)
        none_radio = QRadioButton()
        none_radio.setCursor(Qt.CursorShape.PointingHandCursor)
        none_layout.addWidget(none_radio)
        none_widget.setLayout(none_layout)
        frame_layout.addWidget(none_widget)

        self.none_radio = none_radio
        self.none_label = none_label
        self.button_group.addButton(none_radio)

        for script_name, description in self.mirrors:
            widget = QWidget()
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 2, 0, 2)
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            h_layout.addWidget(desc_label, 1)
            radio = QRadioButton()
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            h_layout.addWidget(radio)
            widget.setLayout(h_layout)
            frame_layout.addWidget(widget)
            self.radio_buttons[script_name] = (radio, desc_label)
            self.button_group.addButton(radio)

        frame_layout.addStretch()
        self.frame.setLayout(frame_layout)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.frame)
        self.setLayout(main_layout)
        self.load_state()

    def load_state(self):
        state_dir = get_state_dir()
        active_script = None
        for script_name in self.radio_buttons.keys():
            if os.path.exists(os.path.join(state_dir, script_name)):
                active_script = script_name
                break

        for script_name, (radio, desc_label) in self.radio_buttons.items():
            desc_label.setProperty("class", "Description")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)

        self.none_label.setProperty("class", "Description")
        self.none_label.style().unpolish(self.none_label)
        self.none_label.style().polish(self.none_label)

        self.none_radio.blockSignals(True)
        self.none_radio.setChecked(True)
        self.none_radio.blockSignals(False)

        if active_script:
            radio, desc_label = self.radio_buttons[active_script]
            desc_label.setProperty("class", "DescriptionGreen")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
        else:
            self.none_label.setProperty("class", "DescriptionGreen")
            self.none_label.style().unpolish(self.none_label)
            self.none_label.style().polish(self.none_label)

    def on_radio_toggled(self, radio, checked):
        if not checked: return
        selected_script = None
        for script_name, (r, desc_label) in self.radio_buttons.items():
            if r == radio:
                selected_script = script_name
                break

        for script_name, (r, lbl) in self.radio_buttons.items():
            if script_name != selected_script:
                if os.path.exists(os.path.join(get_state_dir(), script_name)):
                    lbl.setProperty("class", "DescriptionGreen")
                else:
                    lbl.setProperty("class", "Description")
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)

        if selected_script:
            _, desc_label = self.radio_buttons[selected_script]
            desc_label.setProperty("class", "DescriptionOrange")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
            self.none_label.setProperty("class", "Description")
        else:
            any_flag = any(os.path.exists(os.path.join(get_state_dir(), sn)) for sn in self.radio_buttons.keys())
            self.none_label.setProperty("class", "Description" if any_flag else "DescriptionGreen")

        self.none_label.style().unpolish(self.none_label)
        self.none_label.style().polish(self.none_label)

    def get_selected_mirror_script(self):
        if self.none_radio.isChecked(): return None
        for script_name, (radio, desc_label) in self.radio_buttons.items():
            if radio.isChecked(): return script_name
        return None

class FlathubMirrorCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mirrors = [
            ("26_flathub-alt.sh", "Зеркало ALT Gnome (Россия)"),
            ("27_flathub-ustc.sh", "Зеркало USTC (Китай)"),
            ("28_flathub-default.sh", "Стандартное зеркало (dl.flathub.org)"),
        ]

        self.radio_buttons = {}
        self.button_group = QButtonGroup()
        self.button_group.buttonToggled.connect(self.on_radio_toggled)

        self.frame = QFrame()
        self.frame.setProperty("class", "MirrorCard")

        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(12, 4, 12, 4)

        title = QLabel("Выбор зеркала Flathub")
        title.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        frame_layout.addWidget(title)

        none_widget = QWidget()
        none_layout = QHBoxLayout()
        none_layout.setContentsMargins(0, 2, 0, 2)
        none_label = QLabel("Не менять текущее зеркало")
        none_label.setWordWrap(True)
        none_layout.addWidget(none_label, 1)
        none_radio = QRadioButton()
        none_radio.setCursor(Qt.CursorShape.PointingHandCursor)
        none_layout.addWidget(none_radio)
        none_widget.setLayout(none_layout)
        frame_layout.addWidget(none_widget)

        self.none_radio = none_radio
        self.none_label = none_label
        self.button_group.addButton(none_radio)

        for script_name, description in self.mirrors:
            widget = QWidget()
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 2, 0, 2)
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            h_layout.addWidget(desc_label, 1)
            radio = QRadioButton()
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            h_layout.addWidget(radio)
            widget.setLayout(h_layout)
            frame_layout.addWidget(widget)
            self.radio_buttons[script_name] = (radio, desc_label)
            self.button_group.addButton(radio)

        frame_layout.addStretch()
        self.frame.setLayout(frame_layout)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.frame)
        self.setLayout(main_layout)
        self.load_state()

    def load_state(self):
        state_dir = get_state_dir()
        active_script = None
        for script_name in self.radio_buttons.keys():
            if os.path.exists(os.path.join(state_dir, script_name)):
                active_script = script_name
                break

        for script_name, (radio, desc_label) in self.radio_buttons.items():
            desc_label.setProperty("class", "Description")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)

        self.none_label.setProperty("class", "Description")
        self.none_label.style().unpolish(self.none_label)
        self.none_label.style().polish(self.none_label)

        self.none_radio.blockSignals(True)
        self.none_radio.setChecked(True)
        self.none_radio.blockSignals(False)

        if active_script:
            radio, desc_label = self.radio_buttons[active_script]
            desc_label.setProperty("class", "DescriptionGreen")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
        else:
            self.none_label.setProperty("class", "DescriptionGreen")
            self.none_label.style().unpolish(self.none_label)
            self.none_label.style().polish(self.none_label)

    def on_radio_toggled(self, radio, checked):
        if not checked: return
        selected_script = None
        for script_name, (r, desc_label) in self.radio_buttons.items():
            if r == radio:
                selected_script = script_name
                break

        for script_name, (r, lbl) in self.radio_buttons.items():
            if script_name != selected_script:
                if os.path.exists(os.path.join(get_state_dir(), script_name)):
                    lbl.setProperty("class", "DescriptionGreen")
                else:
                    lbl.setProperty("class", "Description")
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)

        if selected_script:
            _, desc_label = self.radio_buttons[selected_script]
            desc_label.setProperty("class", "DescriptionOrange")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
            self.none_label.setProperty("class", "Description")
        else:
            any_flag = any(os.path.exists(os.path.join(get_state_dir(), sn)) for sn in self.radio_buttons.keys())
            self.none_label.setProperty("class", "Description" if any_flag else "DescriptionGreen")

        self.none_label.style().unpolish(self.none_label)
        self.none_label.style().polish(self.none_label)

    def get_selected_mirror_script(self):
        if self.none_radio.isChecked(): return None
        for script_name, (radio, desc_label) in self.radio_buttons.items():
            if radio.isChecked(): return script_name
        return None

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Справка - Alt KDE Helper")
        self.setMinimumSize(730, 630)
        self.resize(780, 680)
        self.setModal(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setOpenExternalLinks(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        help_path = get_help_path()
        try:
            with open(help_path, 'r', encoding='utf-8') as f:
                help_html = f.read()
        except Exception as e:
            help_html = f"<h1>Ошибка</h1><p>Не удалось загрузить справку: {e}</p>"

        self.label.setText(help_html)
        scroll.setWidget(self.label)
        layout.addWidget(scroll)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

class CategoryPage(QWidget):
    def __init__(self, cards, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        content_layout.setContentsMargins(10, 5, 10, 5)

        for card in cards:
            content_layout.addWidget(card)

        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.setLayout(layout)
        self.cards = cards
        self.worker = None
        self._closing = False

class AppearancePage(QWidget):
    """Страница оформления с кнопками управления панелью и дополнительными настройками"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        content_layout.setContentsMargins(10, 5, 10, 5)

        # --- Блок 1: Настройка панели ---
        title = QLabel("<b>Настройка панели</b>")
        title.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        content_layout.addWidget(title)

        self.btn_editable_tray = QPushButton("Сделать область уведомления редактируемой")
        self.btn_editable_tray.setProperty("class", "BottomButton")
        self.btn_editable_tray.setMinimumHeight(40)
        self.btn_editable_tray.setToolTip("Позволяет перемещать значки громкости, раскладки клавиатуры,\nподключенных устройств в режиме редактирования панели.\n\nДобавленные вручную виджеты будут удалены,\nнадо будет добавить их заново.")
        content_layout.addWidget(self.btn_editable_tray)

        self.btn_save_panel = QPushButton("Сохранить настройки виджетов панели")
        self.btn_save_panel.setProperty("class", "BottomButton")
        self.btn_save_panel.setMinimumHeight(40)
        self.btn_save_panel.setToolTip("Сохраняет текущие настройки панели и виджетов\nв архив tar.gz. Выберите путь и имя файла.")
        content_layout.addWidget(self.btn_save_panel)

        self.btn_load_panel = QPushButton("Загрузить настройки виджетов панели")
        self.btn_load_panel.setProperty("class", "BottomButton")
        self.btn_load_panel.setMinimumHeight(40)
        self.btn_load_panel.setToolTip("Загружает настройки панели из ранее сохранённого\nархива tar.gz. Выберите файл архива.")
        content_layout.addWidget(self.btn_load_panel)

        self.btn_reset_panel = QPushButton("Вернуть расположение виджетов по умолчанию")
        self.btn_reset_panel.setProperty("class", "BottomButton")
        self.btn_reset_panel.setMinimumHeight(40)
        self.btn_reset_panel.setToolTip("Удаляет текущие настройки панели и восстанавливает\nзаводские настройки по умолчанию.\n\nДобавленные вручную виджеты будут удалены.")
        content_layout.addWidget(self.btn_reset_panel)

        content_layout.addSpacing(10)

        # --- Визуальный разделитель 1 ---
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        line1.setStyleSheet("background-color: palette(mid); margin-top: 10px; margin-bottom: 10px;")
        content_layout.addWidget(line1)

        # --- Блок 2: Современный интерфейс ---
        content_layout.addSpacing(10)

        # 1. Кнопки цветов
        self.btn_modern_light = QPushButton("Светлая панель и светлые окна")
        self.btn_modern_light.setProperty("class", "BottomButton")
        self.btn_modern_light.setMinimumHeight(40)
        self.btn_modern_light.setToolTip("Применяет светлые цвета, тему Breeze и иконки Papirus.")
        content_layout.addWidget(self.btn_modern_light)

        self.btn_modern_mixed = QPushButton("Тёмная панель и светлые окна")
        self.btn_modern_mixed.setProperty("class", "BottomButton")
        self.btn_modern_mixed.setMinimumHeight(40)
        self.btn_modern_mixed.setToolTip("Применяет тёмную панель, светлые окна, тему Breeze и иконки Papirus.")
        content_layout.addWidget(self.btn_modern_mixed)

        self.btn_modern_dark = QPushButton("Тёмная панель и тёмные окна")
        self.btn_modern_dark.setProperty("class", "BottomButton")
        self.btn_modern_dark.setMinimumHeight(40)
        self.btn_modern_dark.setToolTip("Применяет тёмные цвета, тему Breeze и иконки Papirus.")
        content_layout.addWidget(self.btn_modern_dark)

        content_layout.addSpacing(10)

        # 2. Ряд с кнопками иконок
        icons_btn_layout = QHBoxLayout()
        icons_btn_layout.setSpacing(5)

        self.btn_icons_breeze = QPushButton("Значки Breeze")
        self.btn_icons_breeze.setProperty("class", "BottomButton")
        self.btn_icons_breeze.setMinimumHeight(40)
        self.btn_icons_breeze.setToolTip("Применяет стандартные иконки Breeze.")
        icons_btn_layout.addWidget(self.btn_icons_breeze)

        self.btn_icons_alt = QPushButton("Значки ALT Linux")
        self.btn_icons_alt.setProperty("class", "BottomButton")
        self.btn_icons_alt.setMinimumHeight(40)
        self.btn_icons_alt.setToolTip("Применяет иконки от ALT Linux.")
        icons_btn_layout.addWidget(self.btn_icons_alt)

        self.btn_icons_papirus = QPushButton("Значки Papirus")
        self.btn_icons_papirus.setProperty("class", "BottomButton")
        self.btn_icons_papirus.setMinimumHeight(40)
        self.btn_icons_papirus.setToolTip("Применяет современные иконки Papirus.")
        icons_btn_layout.addWidget(self.btn_icons_papirus)

        content_layout.addLayout(icons_btn_layout)

        content_layout.addSpacing(10)

        # 3. Кнопка сброса
        self.btn_reset_ui = QPushButton("Вернуть настройки тем по умолчанию")
        self.btn_reset_ui.setProperty("class", "BottomButton")
        self.btn_reset_ui.setMinimumHeight(40)
        self.btn_reset_ui.setToolTip("Сбрасывает цвета, тему интерфейса и иконки к стандартным для ALT Linux (BreezeClassic).")
        content_layout.addWidget(self.btn_reset_ui)

        # --- Визуальный разделитель 2 ---
        content_layout.addSpacing(15)
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        line2.setStyleSheet("background-color: palette(mid); margin-top: 10px; margin-bottom: 10px;")
        content_layout.addWidget(line2)

        # --- Блок 3: Дополнительные настройки ---
        content_layout.addSpacing(15)
        extra_title = QLabel("<b>Дополнительные настройки</b>")
        extra_title.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        content_layout.addWidget(extra_title)

        self.cards = []

        # 1. Значки Papirus (remix)
        card_papirus = SimpleActionCard(
            "Установка цветных значков Papirus-Remix",
            "Будут установлены значки Papirus-Remix с разными цветами папок.\nУстановка может занимать несколько минут, из-за большого количества маленьких файлов,\nнаберитесь терпения.",
            "18_install_papirus_icons_action.sh"
        )
        self.cards.append(card_papirus)
        content_layout.addWidget(card_papirus)

        # 2. Профиль Konsole
        card_konsole = SimpleActionCard(
            "Создать профиль Konsole с ярким белым текстом",
            "Создаёт профиль Konsole «Белый_текст» для лучшей читаемости.\nПосле применения перезапустите Konsole или выберите профиль вручную.",
            "25_create_console_profile.sh"
        )
        self.cards.append(card_konsole)
        content_layout.addWidget(card_konsole)

        # 3. Размер шрифта
        card_font = ActionCard(
            "Размер шрифта 10",
            "Устанавливает базовый размер шрифта — 10.\n\nПри нажатии кнопки «Откат» шрифт вернется к стандартному размеру 9.",
            "13_increase_fonts_action.sh",
            "13_increase_fonts_rollback.sh"
        )
        self.cards.append(card_font)
        content_layout.addWidget(card_font)

        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alt KDE Helper")
        self.setObjectName("alt-kde-helper")
        self.setMinimumSize(800, 600)
        self.resize(1070, 710)

        clear_actions_dir()

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_panel = QWidget()
        left_panel.setFixedWidth(180)
        left_panel.setObjectName("LeftPanel")

        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(5)

        self.menu_button = QPushButton()
        self.menu_button.setIcon(QIcon.fromTheme("application-menu"))
        self.menu_button.setIconSize(QSize(22, 22))
        self.menu_button.setFixedSize(40, 40)
        self.menu_button.setToolTip("Меню")
        self.menu_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: palette(alternate-base);
                border: 1px solid palette(mid);
            }
        """)
        self.menu_button.clicked.connect(self.show_menu)

        menu_container = QWidget()
        menu_container.setContentsMargins(0, 0, 0, 0)

        menu_layout = QHBoxLayout()
        menu_layout.setContentsMargins(2, 2, 2, 2)
        menu_layout.setSpacing(5)
        menu_layout.addWidget(self.menu_button)

        menu_label = QLabel("Меню")
        menu_label.setStyleSheet("color: palette(text); font-size: 14px;")
        menu_layout.addWidget(menu_label)
        menu_layout.addStretch()
        menu_container.setLayout(menu_layout)
        left_panel_layout.addWidget(menu_container)

        menu_line = QFrame()
        menu_line.setFrameShape(QFrame.Shape.HLine)
        menu_line.setFrameShadow(QFrame.Shadow.Sunken)
        menu_line.setFixedHeight(0)
        menu_line.setStyleSheet("background-color: palette(window);")
        left_panel_layout.addWidget(menu_line)
        left_panel_layout.addSpacing(20)

        self.tab_btn_maintenance = QPushButton(" Обслуживание")
        self.tab_btn_maintenance.setProperty("class", "TabButtonActive")
        self.tab_btn_maintenance.setCheckable(True)
        self.tab_btn_maintenance.setChecked(True)
        self.tab_btn_maintenance.setMinimumHeight(56)
        self.tab_btn_maintenance.setIcon(QIcon.fromTheme("system-software-update", QIcon.fromTheme("applications-system")))
        self.tab_btn_maintenance.setIconSize(QSize(22, 22))
        self.tab_btn_maintenance.clicked.connect(lambda: self.switch_tab(0))
        left_panel_layout.addWidget(self.tab_btn_maintenance)

        self.tab_btn_fixes = QPushButton(" Настройки")
        self.tab_btn_fixes.setProperty("class", "TabButton")
        self.tab_btn_fixes.setCheckable(True)
        self.tab_btn_fixes.setMinimumHeight(56)
        self.tab_btn_fixes.setIcon(QIcon.fromTheme("preferences-system", QIcon.fromTheme("preferences-other")))
        self.tab_btn_fixes.setIconSize(QSize(22, 22))
        self.tab_btn_fixes.clicked.connect(lambda: self.switch_tab(1))
        left_panel_layout.addWidget(self.tab_btn_fixes)

        self.tab_btn_appearance = QPushButton(" Оформление")
        self.tab_btn_appearance.setProperty("class", "TabButton")
        self.tab_btn_appearance.setCheckable(True)
        self.tab_btn_appearance.setMinimumHeight(56)
        self.tab_btn_appearance.setIcon(QIcon.fromTheme("preferences-desktop-theme", QIcon.fromTheme("preferences-desktop")))
        self.tab_btn_appearance.setIconSize(QSize(22, 22))
        self.tab_btn_appearance.clicked.connect(lambda: self.switch_tab(2))
        left_panel_layout.addWidget(self.tab_btn_appearance)

        left_panel_layout.addSpacing(15)
        _sep = QFrame()
        _sep.setFrameShape(QFrame.Shape.HLine)
        _sep.setFrameShadow(QFrame.Shadow.Sunken)
        _sep.setStyleSheet("background-color: palette(mid); margin-left: 5px; margin-right: 5px;")
        left_panel_layout.addWidget(_sep)
        left_panel_layout.addSpacing(15)

        self.tab_btn_flatpak_backup = QPushButton(" Бэкап Flatpak")
        self.tab_btn_flatpak_backup.setProperty("class", "TabButton")
        self.tab_btn_flatpak_backup.setCheckable(True)
        self.tab_btn_flatpak_backup.setMinimumHeight(56)
        self.tab_btn_flatpak_backup.setIcon(QIcon.fromTheme("document-save", QIcon.fromTheme("drive-harddisk")))
        self.tab_btn_flatpak_backup.setIconSize(QSize(22, 22))
        self.tab_btn_flatpak_backup.clicked.connect(lambda: self.switch_tab(3))
        left_panel_layout.addWidget(self.tab_btn_flatpak_backup)

        self.tab_btn_flatpak_install = QPushButton(" Установка Flatpak")
        self.tab_btn_flatpak_install.setProperty("class", "TabButton")
        self.tab_btn_flatpak_install.setCheckable(True)
        self.tab_btn_flatpak_install.setMinimumHeight(56)
        self.tab_btn_flatpak_install.setIcon(QIcon.fromTheme("system-software-install", QIcon.fromTheme("package-install")))
        self.tab_btn_flatpak_install.setIconSize(QSize(22, 22))
        self.tab_btn_flatpak_install.clicked.connect(lambda: self.switch_tab(4))
        left_panel_layout.addWidget(self.tab_btn_flatpak_install)

        left_panel_layout.addStretch()
        left_panel_layout.addStretch()

        # --- Кнопка отключения sudo ---
        _sep_bottom = QFrame()
        _sep_bottom.setFrameShape(QFrame.Shape.HLine)
        _sep_bottom.setFrameShadow(QFrame.Shadow.Sunken)
        _sep_bottom.setStyleSheet("background-color: palette(mid); margin-left: 5px; margin-right: 5px;")
        left_panel_layout.addWidget(_sep_bottom)

        self.tab_btn_disable_sudo = QPushButton(" Отключить sudo")
        self.tab_btn_disable_sudo.setProperty("class", "TabButton")
        self.tab_btn_disable_sudo.setMinimumHeight(48)

        self.tab_btn_disable_sudo.setStyleSheet("padding-top: 6px; padding-bottom: 10px;")

        # Иконка со щитом
        self.tab_btn_disable_sudo.setIcon(QIcon.fromTheme("security-high", QIcon.fromTheme("system-lock-screen")))
        self.tab_btn_disable_sudo.setIconSize(QSize(22, 22))
        self.tab_btn_disable_sudo.clicked.connect(self.on_disable_sudo)
        left_panel_layout.addWidget(self.tab_btn_disable_sudo)

        left_panel.setLayout(left_panel_layout)

        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.stack = QWidget()
        self.stack_layout = QVBoxLayout()
        self.stack_layout.setContentsMargins(0, 0, 0, 0)

        self.maintenance_page = self.create_maintenance_page()
        self.fixes_page = self.create_fixes_page()
        self.appearance_page = AppearancePage()

        self.appearance_page.btn_editable_tray.clicked.connect(self.on_apply_editable_tray)
        self.appearance_page.btn_save_panel.clicked.connect(self.on_save_panel_settings)
        self.appearance_page.btn_load_panel.clicked.connect(self.on_load_panel_settings)
        self.appearance_page.btn_reset_panel.clicked.connect(self.on_reset_panel_default)

        # Подключаем новые кнопки современного интерфейса
        self.appearance_page.btn_modern_light.clicked.connect(lambda: self.on_apply_modern_ui("light"))
        self.appearance_page.btn_modern_mixed.clicked.connect(lambda: self.on_apply_modern_ui("mixed"))
        self.appearance_page.btn_modern_dark.clicked.connect(lambda: self.on_apply_modern_ui("dark"))
        self.appearance_page.btn_icons_breeze.clicked.connect(self.on_apply_breeze_icons)
        self.appearance_page.btn_icons_alt.clicked.connect(self.on_apply_alt_icons)
        self.appearance_page.btn_icons_papirus.clicked.connect(self.on_apply_papirus_icons)
        self.appearance_page.btn_reset_ui.clicked.connect(self.on_reset_to_default)

        self.flatpak_backup_page = FlatpakBackupPage()
        self.flatpak_install_page = FlatpakInstallPage()

        self.stack_layout.addWidget(self.maintenance_page)
        self.stack_layout.addWidget(self.fixes_page)
        self.stack_layout.addWidget(self.appearance_page)
        self.stack_layout.addWidget(self.flatpak_backup_page)
        self.stack_layout.addWidget(self.flatpak_install_page)

        self.fixes_page.setVisible(False)
        self.appearance_page.setVisible(False)
        self.flatpak_backup_page.setVisible(False)
        self.flatpak_install_page.setVisible(False)

        self.stack.setLayout(self.stack_layout)
        right_layout.addWidget(self.stack, 1)

        bottom_layout = QHBoxLayout()
        self.bottom_line = QFrame()
        self.bottom_line.setFrameShape(QFrame.Shape.HLine)
        self.bottom_line.setFrameShadow(QFrame.Shadow.Sunken)
        self.bottom_line.setFixedHeight(1)
        right_layout.addWidget(self.bottom_line)

        bottom_layout.setContentsMargins(0, 10, 10, 10)
        bottom_layout.setSpacing(10)
        bottom_layout.addStretch()

        self.recommended_btn = QPushButton("Выбрать рекомендованные настройки")
        self.recommended_btn.setProperty("class", "BottomButton")
        self.recommended_btn.clicked.connect(self.toggle_recommended)
        bottom_layout.addWidget(self.recommended_btn)
        bottom_layout.addSpacing(10)

        self.apply_btn = QPushButton(" Применить")
        self.apply_btn.setIcon(QIcon.fromTheme("dialog-ok"))
        self.apply_btn.setProperty("class", "BottomButton")
        self.apply_btn.setToolTip("После нажатия кнопки откроется терминал.\nВ нём будут выполняться указанные задания.\nДождитесь надписи об окончании, не закрывайте терминал раньше.")
        self.apply_btn.clicked.connect(self.apply_actions)
        bottom_layout.addWidget(self.apply_btn)

        right_layout.addLayout(bottom_layout)
        right_widget.setLayout(right_layout)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_widget, 1)

        line_v = QFrame()
        line_v.setFrameShape(QFrame.Shape.VLine)
        line_v.setFrameShadow(QFrame.Shadow.Sunken)
        line_v.setFixedWidth(1)
        main_layout.addWidget(line_v)

        central.setLayout(main_layout)

        self.recommended_scripts = [
            "05_update_system_action.sh",
            "07_install_packages_action.sh",
            "21_install_openh264_action.sh",
            "16_flatpak_chrome_3d_action.sh",
            "17_enable_ghns_action.sh",
            "08_add_groups_action.sh",
            "29_add_actions_dolphin_action.sh",
            "06_install_eepm_action.sh",
            "11_flatpak_home_access_action.sh",
            "12_fix_copy_indicator_action.sh",
            "25_create_console_profile.sh",
            "13_increase_fonts_action.sh"
        ]
        self.recommended_state = False
        self.help_dialog = None

        BUSY.changed.connect(self._on_busy_changed)

        self.run_check_state()
        ensure_packages_file(self)

        for card in self.get_all_cards():
            if hasattr(card, 'load_state'):
                card.load_state()
        self.update_maint_master_state()

        from threading import Thread
        Thread(target=self.check_updates_background, daemon=True).start()

    def _on_busy_changed(self, busy):
        """Блокирует кнопки применения, пока работает konsole."""
        self.apply_btn.setEnabled(not busy)
        self.recommended_btn.setEnabled(not busy)

    def showEvent(self, event):
        super().showEvent(event)
        QApplication.instance().setStyleSheet(get_stylesheet())

    def event(self, event):
        if event.type() == QEvent.Type.ApplicationPaletteChange:
            QApplication.instance().setStyleSheet(get_stylesheet())
            return True
        return super().event(event)

    def show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { menu-scrollable: 1; }")

        edit_packages_action = QAction("Редактировать список пакетов", self)
        edit_packages_action.triggered.connect(self.edit_packages_list)
        menu.addAction(edit_packages_action)

        reset_packages_action = QAction("Восстановить список пакетов по умолчанию", self)
        reset_packages_action.triggered.connect(self.reset_packages_list)
        menu.addAction(reset_packages_action)

        open_folder_action = QAction("Открыть папку настроек", self)
        open_folder_action.triggered.connect(self.open_packages_folder)
        menu.addAction(open_folder_action)

        menu.addSeparator()

        check_updates_action = QAction("Проверить обновление", self)
        check_updates_action.triggered.connect(self.check_for_updates)
        menu.addAction(check_updates_action)

        menu.addSeparator()

        help_action = QAction("Справка", self)
        help_action.triggered.connect(self.show_help)
        menu.addAction(help_action)

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)

        # --- Новый пункт ---
        donate_action = QAction("Поддержать разработчика", self)
        donate_action.triggered.connect(self.show_donate_dialog)
        menu.addAction(donate_action)
        # -------------------

        menu.exec(self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height())))

    def on_disable_sudo(self):
        reply = QMessageBox.warning(self, "Отключение sudo",
            "Вы собираетесь отключить sudo для ВСЕХ пользователей системы.\n\n"
            "Эта программа не может полноценно работать без sudo и будет закрыта.\n\n"
            "Чтобы снова включить sudo, просто запустите программу, она в первом окне предложит это сделать.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            BUSY.acquire()
            try:
                # Используем bash -c и полный путь к control для надежности
                res = subprocess.run(
                    ['pkexec', 'bash', '-c', '/usr/sbin/control sudowheel disabled'],
                    capture_output=True,
                    text=True
                )

                if res.returncode == 0:
                    QMessageBox.information(self, "Готово", "Sudo успешно отключён для всех пользователей.\n\nПрограмма будет закрыта.")
                    sys.exit(0)
                else:
                    # Показываем реальную ошибку, чтобы понять, что не так
                    error_detail = res.stderr.strip() if res.stderr.strip() else f"Код возврата: {res.returncode}"
                    QMessageBox.critical(self, "Ошибка", f"Не удалось отключить sudo.\n\nДетали:\n{error_detail}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{e}")
            finally:
                BUSY.release()

    def switch_tab(self, index):
        self.maintenance_page.setVisible(index == 0)
        self.fixes_page.setVisible(index == 1)
        self.appearance_page.setVisible(index == 2)
        self.flatpak_backup_page.setVisible(index == 3)
        self.flatpak_install_page.setVisible(index == 4)

        tab_buttons = [
            self.tab_btn_maintenance,
            self.tab_btn_fixes,
            self.tab_btn_appearance,
            self.tab_btn_flatpak_backup,
            self.tab_btn_flatpak_install,
        ]
        for i, btn in enumerate(tab_buttons):
            btn.setProperty("class", "TabButtonActive" if index == i else "TabButton")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Нижняя панель не имеет смысла на вкладках Flatpak
        show_bottom = index < 3
        self.recommended_btn.setVisible(show_bottom)
        self.apply_btn.setVisible(show_bottom)
        self.bottom_line.setVisible(show_bottom)
        if index == 2:
            self.update_theme_checkmarks()

    def get_all_cards(self):
        cards = []
        if hasattr(self.maintenance_page, 'cards'):
            cards.extend(self.maintenance_page.cards)
        if hasattr(self.fixes_page, 'cards'):
            cards.extend(self.fixes_page.cards)
        if hasattr(self.appearance_page, 'cards'):
            cards.extend(self.appearance_page.cards)
        return cards

    def get_mirror_card(self):
        for card in self.get_all_cards():
            if isinstance(card, MirrorCard):
                return card
        return None

    def get_flathub_mirror_card(self):
        for card in self.get_all_cards():
            if isinstance(card, FlathubMirrorCard):
                return card
        return None

    def toggle_recommended(self):
        cards = self.get_all_cards()
        if not self.recommended_state:
            for card in cards:
                if hasattr(card, 'install_cb') and hasattr(card, 'script_name'):
                    if card.script_name in self.recommended_scripts:
                        card.install_cb.setChecked(True)
            self.recommended_state = True
        else:
            for card in cards:
                if hasattr(card, 'install_cb') and hasattr(card, 'script_name'):
                    if card.script_name in self.recommended_scripts:
                        card.install_cb.setChecked(False)
            self.recommended_state = False
        self.update_maint_master_state()

    def update_maint_master_state(self, state=None):
        if not hasattr(self, 'maint_target_cards') or not hasattr(self, 'maint_master_cb'):
            return
        checked = sum(1 for c in self.maint_target_cards if c.install_cb.isChecked())
        total = len(self.maint_target_cards)
        if checked == 0:
            new_state = Qt.CheckState.Unchecked
        elif checked == total:
            new_state = Qt.CheckState.Checked
        else:
            new_state = Qt.CheckState.PartiallyChecked
        self.maint_master_cb.blockSignals(True)
        self.maint_master_cb.setCheckState(new_state)
        self.maint_master_cb.blockSignals(False)

    def on_maint_master_clicked(self, checked):
        for card in self.maint_target_cards:
            card.install_cb.blockSignals(True)
            card.install_cb.setChecked(checked)
            card.install_cb.blockSignals(False)
            state_val = Qt.CheckState.Checked.value if checked else Qt.CheckState.Unchecked.value
            card.on_install_changed(state_val)
        self.update_maint_master_state()

    def apply_actions(self):
        actions_dir = get_actions_dir()
        scripts_dir = get_scripts_dir()
        clear_actions_dir()

        for page in [self.maintenance_page, self.fixes_page, self.appearance_page]:
            for card in page.cards:
                if hasattr(card, 'install_cb') and card.install_cb.isChecked():
                    script_src = os.path.join(scripts_dir, card.script_name)
                    action_path = os.path.join(actions_dir, card.script_name)
                    if os.path.exists(script_src) and not os.path.exists(action_path):
                        copy_and_patch(script_src, action_path, actions_dir)
                if hasattr(card, 'rollback_cb') and card.rollback_cb.isChecked():
                    script_src = os.path.join(scripts_dir, card.rollback_script_name)
                    action_path = os.path.join(actions_dir, card.rollback_script_name)
                    if os.path.exists(script_src) and not os.path.exists(action_path):
                        copy_and_patch(script_src, action_path, actions_dir)

        update_system_checked = False
        for card in self.maintenance_page.cards:
            if hasattr(card, 'script_name') and card.script_name == "05_update_system_action.sh":
                if hasattr(card, 'install_cb') and card.install_cb.isChecked():
                    update_system_checked = True
                break

        if update_system_checked:
            for pkg, script in [("eepm", "06_update_eepm_action.sh"), ("flatpak", "10_update_flatpak_action.sh"), ("stplr", "20_update_stplr_action.sh")]:
                if subprocess.run(f"rpm -q {pkg}", shell=True, capture_output=True).returncode == 0:
                    script_src = os.path.join(scripts_dir, script)
                    action_path = os.path.join(actions_dir, script)
                    if os.path.exists(script_src) and not os.path.exists(action_path):
                        copy_and_patch(script_src, action_path, actions_dir)

            update_script = "30_update_appimage_action.sh"
            script_src = os.path.join(scripts_dir, update_script)
            action_path = os.path.join(actions_dir, update_script)
            if os.path.exists(script_src) and not os.path.exists(action_path):
                copy_and_patch(script_src, action_path, actions_dir)

        mirror_card = self.get_mirror_card()
        if mirror_card:
            selected_script = mirror_card.get_selected_mirror_script()
            if selected_script:
                script_src = os.path.join(scripts_dir, selected_script)
                action_path = os.path.join(actions_dir, selected_script)
                if os.path.exists(script_src) and not os.path.exists(action_path):
                    copy_and_patch(script_src, action_path, actions_dir)

        flathub_mirror_card = self.get_flathub_mirror_card()
        if flathub_mirror_card:
            selected_script = flathub_mirror_card.get_selected_mirror_script()
            if selected_script:
                script_src = os.path.join(scripts_dir, selected_script)
                action_path = os.path.join(actions_dir, selected_script)
                if os.path.exists(script_src) and not os.path.exists(action_path):
                    copy_and_patch(script_src, action_path, actions_dir)

        action_files = [f for f in os.listdir(actions_dir) if f.endswith('.sh') and f != '99_final.sh']
        if not action_files:
            QMessageBox.information(self, "Нет действий", "Нет действий для применения.")
            return

        final_script_src = os.path.join(scripts_dir, '99_final.sh')
        final_script_dst = os.path.join(actions_dir, '99_final.sh')
        if os.path.exists(final_script_src) and not os.path.exists(final_script_dst):
            copy_and_patch(final_script_src, final_script_dst, actions_dir)

        self.current_worker = ActionWorker(actions_dir)
        self.current_worker.finished.connect(self.on_actions_finished)
        self.current_worker.start()

    def on_actions_finished(self):
        if hasattr(self.maintenance_page, '_closing') and self.maintenance_page._closing: return
        if hasattr(self.fixes_page, '_closing') and self.fixes_page._closing: return

        actions_dir = get_actions_dir()
        scripts_dir = get_scripts_dir()
        final_path = os.path.join(actions_dir, '99_final.sh')
        if os.path.exists(final_path): os.remove(final_path)

        remaining = [f for f in os.listdir(actions_dir) if f.endswith('.sh')]
        if not remaining:
            self.reinitialize_program()
            return

        script_names = [f"  • {script.replace('_action.sh', '').replace('_rollback.sh', '')}" for script in sorted(remaining)]
        scripts_list = "\n".join(script_names)

        msg_box = QMessageBox()
        msg_box.setWindowTitle("Не все действия выполнены")
        msg_box.setText(f"Остались невыполненные действия:\n\n{scripts_list}\n\nПродолжить выполнение или отменить?")
        msg_box.setInformativeText("При продолжении будет произведена повторная попытка выполнить оставшиеся действия.")
        continue_btn = msg_box.addButton("Продолжить", QMessageBox.ButtonRole.YesRole)
        cancel_btn = msg_box.addButton("Отменить", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(continue_btn)
        msg_box.exec()

        if msg_box.clickedButton() == continue_btn:
            final_script_src = os.path.join(scripts_dir, '99_final.sh')
            final_script_dst = os.path.join(actions_dir, '99_final.sh')
            if os.path.exists(final_script_src) and not os.path.exists(final_script_dst):
                copy_and_patch(final_script_src, final_script_dst, actions_dir)
            self.current_worker = ActionWorker(actions_dir)
            self.current_worker.finished.connect(self.on_actions_finished)
            self.current_worker.start()
        else:
            self.reinitialize_program()

    def reinitialize_program(self):
        clear_actions_dir()
        for card in self.get_all_cards():
            if hasattr(card, 'install_cb'):
                card.install_cb.blockSignals(True)
                card.install_cb.setChecked(False)
                card.install_cb.blockSignals(False)
            if hasattr(card, 'rollback_cb'):
                card.rollback_cb.blockSignals(True)
                card.rollback_cb.setChecked(False)
                card.rollback_cb.blockSignals(False)
        self.run_check_state()
        for card in self.get_all_cards():
            if hasattr(card, 'load_state'): card.load_state()

        mirror_card = self.get_mirror_card()
        if mirror_card and hasattr(mirror_card, 'none_radio'):
            mirror_card.none_radio.blockSignals(True)
            mirror_card.none_radio.setChecked(True)
            mirror_card.none_radio.blockSignals(False)
            if hasattr(mirror_card, 'load_state'): mirror_card.load_state()

        flathub_mirror_card = self.get_flathub_mirror_card()
        if flathub_mirror_card and hasattr(flathub_mirror_card, 'none_radio'):
            flathub_mirror_card.none_radio.blockSignals(True)
            flathub_mirror_card.none_radio.setChecked(True)
            flathub_mirror_card.none_radio.blockSignals(False)
            if hasattr(flathub_mirror_card, 'load_state'): flathub_mirror_card.load_state()

        self.recommended_state = False
        self.update_maint_master_state()

    def run_check_state(self):
        scripts_dir = get_scripts_dir()
        check_script = os.path.join(scripts_dir, 'check_state.sh')
        if os.path.exists(check_script):
            subprocess.run(['bash', check_script], capture_output=True)

    def show_help(self):
        if self.help_dialog is None:
            self.help_dialog = HelpDialog(self)
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def show_about(self):
        QMessageBox.about(self, "О программе Alt KDE Helper",
            f"<b>Alt KDE Helper</b><br><br>"
            f"Версия: {get_version()}<br><br>"
            "Программа для настройки и обслуживания<br>"
            "ALT Linux 11 с рабочим столом KDE6<br><br>"
            "Автор: kullibbin<br>"
            "<a href='mailto:kullibbin@gmail.com'>kullibbin@gmail.com</a><br><br>"
            "<a href='https://t.me/Alt_KDE_Helper'>Telegram-канал</a> (новости и поддержка)<br><br>"  # <--- Вот здесь добавлен <br>
            "<a href='https://github.com/kullibbin-hub/alt-kde-helper'>GitHub</a>")

    def show_donate_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Поддержать разработчика")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        title = QLabel("<b>Спасибо, что пользуетесь Alt KDE Helper!</b>")
        title.setStyleSheet("font-size: 14px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        text = QLabel(
            "Если программа сэкономила вам время и сделала систему удобнее,     \n"
            "вы можете поддержать автора донатом.\n"
            "Это помогает выделять время на тестирование,\n"
            "исправление багов и разработку новых функций."
        )
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)

        layout.addSpacing(10)

        # Путь к картинке с QR-кодом
        qr_path = '/opt/alt-kde-helper/usr/share/alt-kde-helper/donate_qr.png'

        if os.path.exists(qr_path):
            pixmap = QPixmap(qr_path)
            # Если картинка слишком большая, уменьшаем её до 250x250
            if pixmap.width() > 250:
                pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            qr_label = QLabel()
            qr_label.setPixmap(pixmap)
            qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(qr_label)

            qr_hint = QLabel("Отсканируйте QR-код в приложении вашего банка (СБП)")
            qr_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Убрали setStyleSheet, теперь цвет обычный (palette(text))
            layout.addWidget(qr_hint)
        else:
            # Если картинки нет, выводим заглушку
            fallback = QLabel("<i>(QR-код временно недоступен)</i>")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(fallback)

        layout.addSpacing(15)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        dialog.setLayout(layout)
        dialog.exec()

    def check_updates_background(self):
        import urllib.request, json, subprocess
        current_version = get_version()
        try:
            req = urllib.request.Request("https://api.github.com/repos/kullibbin-hub/alt-kde-helper/releases/latest", headers={"User-Agent": "Alt KDE Helper"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").lstrip("v")
                if latest_version and latest_version > current_version:
                    subprocess.Popen(["kdialog", "--passivepopup", f"Доступна новая версия Alt KDE Helper: {latest_version}\nПерейдите в меню → Проверить обновление.", "5"])
        except: pass

    def check_for_updates(self):
        import urllib.request, json, subprocess, os, sys
        current_version = get_version()
        try:
            req = urllib.request.Request("https://api.github.com/repos/kullibbin-hub/alt-kde-helper/releases/latest", headers={"User-Agent": "Alt KDE Helper"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").lstrip("v")
                release_url = data.get("html_url", "")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось проверить обновления:\n{str(e)}")
            return

        if not latest_version:
            QMessageBox.warning(self, "Ошибка", "Не удалось определить версию на GitHub")
            return
        if latest_version <= current_version:
            QMessageBox.information(self, "Обновлений нет", f"У вас последняя версия {current_version}")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Доступно обновление")
        msg.setText(f"Доступна новая версия: {latest_version}\n\nВаша версия: {current_version}")
        msg.setInformativeText("Установить обновление?")
        install_btn = msg.addButton("Установить", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(install_btn)
        msg.exec()

        if msg.clickedButton() != install_btn: return

        download_dir = os.path.expanduser("~/Загрузки")
        if not os.path.exists(download_dir): download_dir = os.path.expanduser("~/Downloads")
        rpm_filename = f"alt-kde-helper-{latest_version}-alt1.noarch.rpm"
        rpm_path = os.path.join(download_dir, rpm_filename)
        rpm_url = f"https://github.com/kullibbin-hub/alt-kde-helper/releases/download/v{latest_version}/{rpm_filename}"

        cmd = (f"echo 'Скачивание обновления...' && "
               f"wget -q -O '{rpm_path}' '{rpm_url}' && "
               f"echo '' && echo 'Установка обновления...' && "
               f"sudo apt-get install -y '{rpm_path}' && "
               f"echo '' && echo '✅ Обновление установлено успешно!' && "
               f"echo 'Пакет сохранён в: {rpm_path}' && echo '' && "
               f"echo 'Нажмите любую клавишу для выхода...' && read -n 1")

        BUSY.acquire()
        try:
            process = subprocess.Popen(['konsole', '--separate', '--title', 'Установка обновления', '-e', 'bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()
            rc = process.returncode
        finally:
            BUSY.release()

        if rc == 0:
            restart_msg = QMessageBox(self)
            restart_msg.setWindowTitle("Обновление установлено")
            restart_msg.setText(f"Пакет скачан в:\n{rpm_path}\n\nОбновление до версии {latest_version} установлено успешно!")
            restart_msg.setInformativeText("Для применения изменений перезапустите программу.")
            restart_btn = restart_msg.addButton("Перезапустить", QMessageBox.ButtonRole.AcceptRole)
            restart_msg.addButton("Закрыть", QMessageBox.ButtonRole.RejectRole)
            restart_msg.setDefaultButton(restart_btn)
            restart_msg.exec()
            if restart_msg.clickedButton() == restart_btn:
                os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось установить обновление. Подробности смотрите в терминале.")

    def edit_packages_list(self):
        import subprocess
        packages_file = get_packages_file_path()
        config_dir = get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        if not os.path.exists(packages_file):
            default_file = get_default_packages_path()
            if os.path.exists(default_file): shutil.copy2(default_file, packages_file)
            else: open(packages_file, 'w').close()
        editor = 'kate' if subprocess.run(['which', 'kate'], capture_output=True).returncode == 0 else 'kwrite'
        subprocess.Popen([editor, packages_file])

    def reset_packages_list(self):
        config_dir = get_config_dir()
        current_version = get_current_version()
        current_file = get_packages_file_path()
        backup_file = os.path.join(config_dir, f'user_packages_{current_version}.old.txt')
        default_file = get_default_packages_path()

        dialog = QDialog(self)
        dialog.setWindowTitle("Восстановление списка пакетов")
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Восстановление списка пакетов по умолчанию</b>"))
        layout.addSpacing(10)
        layout.addWidget(QLabel("Вы хотите заменить ваш текущий список пакетов на стандартный список по умолчанию (который идёт с программой)."))
        layout.addSpacing(15)
        backup_info = QLabel(f'📁 <b>Ваш текущий список не будет удалён.</b><br>Он будет сохранён в той же папке как:<br><tt>user_packages_{current_version}.old.txt</tt><br><br>Папка с настройками: <a href="file://{config_dir}">{config_dir}</a><br><br>Если вы передумаете, вы сможете удалить новый список, а ваш старый<br>переименовать обратно в <tt>user_packages_{current_version}.txt</tt> вручную.')
        backup_info.setWordWrap(True)
        backup_info.setOpenExternalLinks(True)
        layout.addWidget(backup_info)
        layout.addSpacing(20)
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Восстановить")
        cancel_btn = QPushButton("Отмена")
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        ok_btn.clicked.connect(lambda: dialog.done(1))
        cancel_btn.clicked.connect(lambda: dialog.done(0))

        if dialog.exec() == 1:
            if os.path.exists(backup_file): os.remove(backup_file)
            if os.path.exists(current_file): os.rename(current_file, backup_file)
            if os.path.exists(default_file): shutil.copy2(default_file, current_file)
            else: open(current_file, 'w').close()
            QMessageBox.information(self, "Готово", "Список пакетов восстановлен.\n\nВаш старый список сохранён как .old.txt")

    def open_packages_folder(self):
        config_dir = get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(config_dir))

    def restart_plasmashell(self):
        # Запускаем ровно ту цепочку, которая гарантированно работает
        subprocess.Popen(
            ['bash', '-c', 'kquitapp6 plasmashell && kstart plasmashell'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def on_apply_editable_tray(self):
        target_file = os.path.expanduser(f'~/.config/{PANEL_CONFIG_FILENAME}')
        if not os.path.exists(PRESET_FILE_PATH):
            QMessageBox.critical(self, "Ошибка", f"Файл пресета не найден:\n{PRESET_FILE_PATH}")
            return
        try:
            shutil.copy2(PRESET_FILE_PATH, target_file)
            self.restart_plasmashell()
            QMessageBox.information(self, "Готово", "Пресет с редактируемым треем применён.\nПанель перезапущена.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось применить пресет:\n{e}")

    def on_save_panel_settings(self):
        source_file = os.path.expanduser(f'~/.config/{PANEL_CONFIG_FILENAME}')
        if not os.path.exists(source_file):
            QMessageBox.warning(self, "Ошибка", f"Файл настроек панели не найден:\n{source_file}\nНечего сохранять.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить настройки панели", os.path.expanduser("~/"), "Архив tar.gz (*.tar.gz)", options=QFileDialog.Option.DontUseNativeDialog)
        if not file_path: return
        if not file_path.endswith('.tar.gz'): file_path += '.tar.gz'
        try:
            with tarfile.open(file_path, 'w:gz') as tar:
                tar.add(source_file, arcname=PANEL_CONFIG_FILENAME)
            QMessageBox.information(self, "Готово", f"Настройки панели сохранены в:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки:\n{e}")

    def on_load_panel_settings(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Загрузить настройки панели", os.path.expanduser("~/"), "Архив tar.gz (*.tar.gz)", options=QFileDialog.Option.DontUseNativeDialog)
        if not file_path or not os.path.exists(file_path):
            if file_path: QMessageBox.critical(self, "Ошибка", f"Файл не найден:\n{file_path}")
            return
        try:
            with tarfile.open(file_path, 'r:gz') as tar:
                members = tar.getnames()
                found = any(os.path.basename(member) == PANEL_CONFIG_FILENAME for member in members)
                if not found:
                    QMessageBox.critical(self, "Ошибка", f"В архиве не найден файл {PANEL_CONFIG_FILENAME}.\nЭто не архив настроек панели.")
                    return
                tar.extractall(path=os.path.expanduser('~/.config'), filter='data')
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось распаковать архив:\n{e}")
            return
        self.restart_plasmashell()
        QMessageBox.information(self, "Готово", "Настройки панели загружены.\nПанель перезапущена.")

    def on_reset_panel_default(self):
        reply = QMessageBox.question(self, "Подтверждение", "Добавленные вручную виджеты будут удалены.\n\nПродолжить?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        target_file = os.path.expanduser(f'~/.config/{PANEL_CONFIG_FILENAME}')
        try:
            if os.path.exists(target_file): os.remove(target_file)
            self.restart_plasmashell()
            QMessageBox.information(self, "Готово", "Расположение виджетов возвращено к заводским настройкам.\nПанель перезапущена.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сбросить настройки:\n{e}")

    def _is_dark_windows(self):
        """Проверяет, темные ли сейчас окна (для выбора правильных иконок)."""
        colorscheme = subprocess.run(['kreadconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', 'ColorScheme'], capture_output=True, text=True).stdout.strip().lower()
        return "dark" in colorscheme

    def _refresh_icons(self):
        """Очищает кэш иконок и перезапускает плазму."""
        subprocess.run(['rm', '-f', os.path.expanduser('~/.cache/icon-cache.kcache')])
        subprocess.run(['kbuildsycoca6', '--noincremental'], capture_output=True)
        subprocess.run(['qdbus-qt6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure'], capture_output=True)
        self.restart_plasmashell()

    def _kread(self, file, group, key):
        """Читает одну настройку KDE. Возвращает строку (пустую при ошибке)."""
        try:
            r = subprocess.run(
                ['kreadconfig6', '--file', file, '--group', group, '--key', key],
                capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""


    def update_theme_checkmarks(self):
        if not hasattr(self.appearance_page, 'btn_modern_light'):
            return

        # 1. Читаем текущее состояние системы
        icons        = self._kread('kdeglobals', 'Icons',   'Theme').lower()
        colorscheme  = self._kread('kdeglobals', 'General', 'ColorScheme').lower()
        theme        = self._kread('plasmarc',   'Theme',   'name').lower()
        widget_style = self._kread('kdeglobals', 'KDE',     'widgetStyle').lower()

        is_breeze_ui = (widget_style == 'breeze')
        is_light_win = colorscheme in ('breezelight', 'breeze')
        is_dark_win  = (colorscheme == 'breezedark')

        # 2. Условия для кнопок цвета.
        #    Если theme == 'default' — ни одна кнопка цвета не загорится (это правильно).
        light_active = (theme == 'breeze')      and is_light_win and is_breeze_ui
        mixed_active = (theme == 'breeze-dark') and is_light_win and is_breeze_ui
        dark_active  = (theme == 'breeze-dark') and is_dark_win  and is_breeze_ui

        # 3. Условия для кнопок иконок (breeze-dark и altos-dark тоже засчитываются)
        is_breeze_icon = 'breeze'  in icons
        is_alt_icon    = 'altos'   in icons
        is_papirus_icon = 'papirus' in icons

        # 4. Условие для сброса — строгое (иконки именно breeze, не breeze-dark)
        is_default = (theme == 'default'
                    and colorscheme == 'breezeclassic'
                    and icons == 'breeze')

        # 5. Функция оформления кнопки
        def set_active(btn, text, active):
            if active:
                btn.setText('✓ ' + text)
                btn.setProperty("active", "true")
            else:
                btn.setText(text)
                btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # 6. Применяем к каждой кнопке
        set_active(self.appearance_page.btn_modern_light,
                'Светлая панель и светлые окна', light_active)
        set_active(self.appearance_page.btn_modern_mixed,
                'Тёмная панель и светлые окна', mixed_active)
        set_active(self.appearance_page.btn_modern_dark,
                'Тёмная панель и тёмные окна', dark_active)

        set_active(self.appearance_page.btn_icons_breeze,
                'Значки Breeze', is_breeze_icon)
        set_active(self.appearance_page.btn_icons_alt,
                'Значки ALT Linux', is_alt_icon)
        set_active(self.appearance_page.btn_icons_papirus,
                'Значки Papirus', is_papirus_icon)

        set_active(self.appearance_page.btn_reset_ui,
                'Вернуть настройки тем по умолчанию', is_default)



    def on_apply_breeze_icons(self):
        is_dark = self._is_dark_windows()
        icon_name = "breeze-dark" if is_dark else "breeze"
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'Icons', '--key', 'Theme', icon_name])
        self._refresh_icons()
        self.update_theme_checkmarks()

    def on_apply_alt_icons(self):
        res = subprocess.run(['rpm', '-q', 'icon-theme-altos'], capture_output=True)
        if res.returncode != 0:
            reply = QMessageBox.question(self, "Иконки ALT не найдены", "Установить пакет icon-theme-altos?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes: return
            BUSY.acquire()
            try:
                cmd = (
                    'echo -e "\\033[1;36m========================================\\033[0m"\n'
                    'echo -e "\\033[1;36mУстановка иконок ALT Linux\\033[0m"\n'
                    'echo -e "\\033[1;36m========================================\\033[0m"\n'
                    '\n'
                    'echo -e "\\033[1;33m→ Обновление списка пакетов...\\033[0m"\n'
                    'sudo apt-get update\n'
                    'if [ $? -ne 0 ]; then\n'
                    '    echo -e "\\033[1;31m❌ Ошибка: не удалось обновить список пакетов\\033[0m"\n'
                    '    echo ""\n'
                    '    echo "Нажмите любую клавишу для выхода..."\n'
                    '    read -n 1\n'
                    '    exit 1\n'
                    'fi\n'
                    '\n'
                    'echo -e "\\033[1;33m→ Установка icon-theme-altos...\\033[0m"\n'
                    'sudo apt-get install -y icon-theme-altos\n'
                    'if [ $? -ne 0 ]; then\n'
                    '    echo -e "\\033[1;31m❌ Ошибка: не удалось установить icon-theme-altos\\033[0m"\n'
                    '    echo ""\n'
                    '    echo "Нажмите любую клавишу для выхода..."\n'
                    '    read -n 1\n'
                    '    exit 1\n'
                    'fi\n'
                    '\n'
                    'echo -e "\\033[1;32m✅ Иконки ALT Linux успешно установлены\\033[0m"\n'
                    'echo ""\n'
                    'echo "Нажмите любую клавишу для выхода..."\n'
                    'read -n 1\n'
                )
                subprocess.Popen(['konsole', '--separate', '--title', 'Установка иконок ALT', '-e', 'bash', '-c', cmd]).wait()
                if subprocess.run(['rpm', '-q', 'icon-theme-altos'], capture_output=True).returncode != 0:
                    QMessageBox.critical(self, "Ошибка", "Не удалось установить пакет. Применение отменено.")
                    return
            finally:
                BUSY.release()

        is_dark = self._is_dark_windows()
        target_icon = "altos-dark" if is_dark else "altos"
        new_icons = target_icon

        # Проверяем точное имя папки
        for d in ["/usr/share/icons", "/usr/local/share/icons", os.path.expanduser("~/.local/share/icons")]:
            if os.path.exists(d):
                for item in os.listdir(d):
                    if item.lower() == target_icon.lower(): new_icons = item
                    elif 'altos' in item.lower() and not new_icons: new_icons = item

        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'Icons', '--key', 'Theme', new_icons])
        self._refresh_icons()
        self.update_theme_checkmarks()

    def on_apply_papirus_icons(self):
        is_dark = self._is_dark_windows()
        target_icon = "Papirus-Dark" if is_dark else "Papirus"
        papirus_theme_name = None
        icon_dirs = ["/usr/share/icons", "/usr/local/share/icons", os.path.expanduser("~/.local/share/icons"), os.path.expanduser("~/.icons")]

        for d in icon_dirs:
            if os.path.exists(d):
                for item in os.listdir(d):
                    if os.path.isdir(os.path.join(d, item)) and item.lower() == target_icon.lower():
                        papirus_theme_name = item
                        break
            if papirus_theme_name: break

        if not papirus_theme_name:
            for d in icon_dirs:
                if os.path.exists(d):
                    for item in os.listdir(d):
                        if 'papirus' in item.lower() and os.path.isdir(os.path.join(d, item)):
                            papirus_theme_name = item
                            break
                if papirus_theme_name: break

        if not papirus_theme_name:
            reply = QMessageBox.question(self, "Иконки не найдены", "Установить иконки Papirus?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes: return
            BUSY.acquire()
            try:
                cmd = (
                    'echo -e "\\033[1;36m========================================\\033[0m"\n'
                    'echo -e "\\033[1;36mУстановка иконок Papirus\\033[0m"\n'
                    'echo -e "\\033[1;36m========================================\\033[0m"\n'
                    '\n'
                    'echo -e "\\033[1;33m→ Обновление списка пакетов...\\033[0m"\n'
                    'sudo apt-get update\n'
                    'if [ $? -ne 0 ]; then\n'
                    '    echo -e "\\033[1;31m❌ Ошибка: не удалось обновить список пакетов\\033[0m"\n'
                    '    echo ""\n'
                    '    echo "Нажмите любую клавишу для выхода..."\n'
                    '    read -n 1\n'
                    '    exit 1\n'
                    'fi\n'
                    '\n'
                    'echo -e "\\033[1;33m→ Установка icon-theme-Papirus и icon-theme-Papirus-Dark...\\033[0m"\n'
                    'sudo apt-get install -y icon-theme-Papirus icon-theme-Papirus-Dark\n'
                    'if [ $? -ne 0 ]; then\n'
                    '    echo -e "\\033[1;31m❌ Ошибка: не удалось установить иконки Papirus\\033[0m"\n'
                    '    echo ""\n'
                    '    echo "Нажмите любую клавишу для выхода..."\n'
                    '    read -n 1\n'
                    '    exit 1\n'
                    'fi\n'
                    '\n'
                    'echo -e "\\033[1;32m✅ Иконки Papirus успешно установлены\\033[0m"\n'
                    'echo ""\n'
                    'echo "Нажмите любую клавишу для выхода..."\n'
                    'read -n 1\n'
                )
                subprocess.Popen(['konsole', '--separate', '--title', 'Установка иконок Papirus', '-e', 'bash', '-c', cmd]).wait()
            finally:
                BUSY.release()
            for d in icon_dirs:
                if os.path.exists(d):
                    for item in os.listdir(d):
                        if os.path.isdir(os.path.join(d, item)) and item.lower() == target_icon.lower():
                            papirus_theme_name = item
                            break
                if papirus_theme_name: break
            if not papirus_theme_name:
                QMessageBox.critical(self, "Ошибка", "Иконки Papirus не были установлены.\nПрименение отменено.")
                return

        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'Icons', '--key', 'Theme', papirus_theme_name])
        self._refresh_icons()
        self.update_theme_checkmarks()

    def on_reset_to_default(self):
        # 1. Удаляем ColorScheme, чтобы plasma-apply-colorscheme
        #    не сказал "уже используется" и не пропустил запись цветов
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals',
                        '--group', 'General', '--key', 'ColorScheme', '--delete'])

        # 2. Применяем схему — физически перезапишет [Colors:*] в kdeglobals
        res = subprocess.run(['plasma-apply-colorscheme', 'BreezeClassic'],
                             capture_output=True)
        if res.returncode != 0:
            # fallback: хотя бы ключ запишем
            subprocess.run(['kwriteconfig6', '--file', 'kdeglobals',
                            '--group', 'General', '--key', 'ColorScheme',
                            'BreezeClassic'])

        # 3. Всё ниже — ПОСЛЕ plasma-apply-colorscheme
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals',
                        '--group', 'Icons', '--key', 'Theme', 'breeze'])
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals',
                        '--group', 'KDE', '--key', 'widgetStyle', 'Breeze'])
        subprocess.run(['kwriteconfig6', '--file', 'plasmarc',
                        '--group', 'Theme', '--key', 'name', 'default'])
        subprocess.run(['kwriteconfig6', '--file', 'kwinrc',
                        '--group', 'org.kde.kdecoration2', '--key', 'library',
                        'org.kde.breeze'])
        subprocess.run(['kwriteconfig6', '--file', 'kwinrc',
                        '--group', 'org.kde.kdecoration2', '--key', 'theme',
                        'Breeze'])

        # 4. WM-цвета — эталонные значения из свежего профиля.
        #    После plasma-apply-colorscheme, потому что он пишет [WM].
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals',
                        '--group', 'WM', '--key', 'activeBackground', '71,80,87'])
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals',
                        '--group', 'WM', '--key', 'activeForeground', '252,252,252'])
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals',
                        '--group', 'WM', '--key', 'inactiveBackground', '239,240,241'])
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals',
                        '--group', 'WM', '--key', 'inactiveForeground', '189,195,199'])

        # 5. Кэш + рестарт плазмы
        self._refresh_icons()

        # 6. Обновить индикаторы на кнопках
        self.update_theme_checkmarks()

        # 7. BreezeClassic — светлые окна, программа тоже светлая
        QApplication.instance().setStyleSheet(get_stylesheet(force_dark=False))

    def on_apply_modern_ui(self, mode="mixed"):
        # 1. Ищем иконки Papirus
        icon_dirs = [
            "/usr/share/icons",
            "/usr/local/share/icons",
            os.path.expanduser("~/.local/share/icons"),
            os.path.expanduser("~/.icons")
        ]

        target_icon_name = "Papirus-Dark" if mode == "dark" else "Papirus"
        target_icon_lower = target_icon_name.lower()

        papirus_theme_name = None
        for d in icon_dirs:
            if os.path.exists(d):
                for item in os.listdir(d):
                    if os.path.isdir(os.path.join(d, item)) and item.lower() == target_icon_lower:
                        papirus_theme_name = item
                        break
            if papirus_theme_name:
                break

        if not papirus_theme_name:
            for d in icon_dirs:
                if os.path.exists(d):
                    for item in os.listdir(d):
                        if 'papirus' in item.lower() and os.path.isdir(os.path.join(d, item)):
                            papirus_theme_name = item
                            break
                if papirus_theme_name:
                    break

        # 2. Установка иконок при необходимости
        if not papirus_theme_name:
            reply = QMessageBox.question(self, "Иконки не найдены",
                "Для современного интерфейса нужны иконки Papirus. Они не найдены в системе.\n\n"
                "Установить их сейчас? (Потребуется интернет)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes)

            if reply != QMessageBox.StandardButton.Yes:
                return

            BUSY.acquire()
            try:
                cmd = (
                    'echo -e "\\033[1;36m========================================\\033[0m"\n'
                    'echo -e "\\033[1;36mУстановка иконок Papirus\\033[0m"\n'
                    'echo -e "\\033[1;36m========================================\\033[0m"\n'
                    '\n'
                    'echo -e "\\033[1;33m→ Обновление списка пакетов...\\033[0m"\n'
                    'sudo apt-get update\n'
                    'if [ $? -ne 0 ]; then\n'
                    '    echo -e "\\033[1;31m❌ Ошибка: не удалось обновить список пакетов\\033[0m"\n'
                    '    echo ""\n'
                    '    echo "Нажмите любую клавишу для выхода..."\n'
                    '    read -n 1\n'
                    '    exit 1\n'
                    'fi\n'
                    '\n'
                    'echo -e "\\033[1;33m→ Установка icon-theme-Papirus и icon-theme-Papirus-Dark...\\033[0m"\n'
                    'sudo apt-get install -y icon-theme-Papirus icon-theme-Papirus-Dark\n'
                    'if [ $? -ne 0 ]; then\n'
                    '    echo -e "\\033[1;31m❌ Ошибка: не удалось установить иконки Papirus\\033[0m"\n'
                    '    echo ""\n'
                    '    echo "Нажмите любую клавишу для выхода..."\n'
                    '    read -n 1\n'
                    '    exit 1\n'
                    'fi\n'
                    '\n'
                    'echo -e "\\033[1;32m✅ Иконки Papirus успешно установлены\\033[0m"\n'
                    'echo ""\n'
                    'echo "Нажмите любую клавишу для выхода..."\n'
                    'read -n 1\n'
                )
                process = subprocess.Popen(
                    ['konsole', '--separate', '--title', 'Установка иконок Papirus', '-e', 'bash', '-c', cmd]
                )
                process.wait()
            finally:
                BUSY.release()

            for d in icon_dirs:
                if os.path.exists(d):
                    for item in os.listdir(d):
                        if os.path.isdir(os.path.join(d, item)) and item.lower() == target_icon_lower:
                            papirus_theme_name = item
                            break
                if papirus_theme_name:
                    break

            if not papirus_theme_name:
                for d in icon_dirs:
                    if os.path.exists(d):
                        for item in os.listdir(d):
                            if 'papirus' in item.lower() and os.path.isdir(os.path.join(d, item)):
                                papirus_theme_name = item
                                break
                    if papirus_theme_name:
                        break

            if not papirus_theme_name:
                QMessageBox.critical(self, "Ошибка",
                    "Иконки Papirus не были установлены (возможно, нет интернета или вы закрыли терминал).\n"
                    "Применение отменено.")
                return

        # 3. Сохраняем старые настройки (ТОЛЬКО ЕСЛИ ФАЙЛА ЕЩЕ НЕТ)
        config_dir = get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        backup_file = os.path.join(config_dir, 'ui_backup.txt')

        if not os.path.exists(backup_file):
            font_keys = ['font', 'menuFont', 'toolbarFont', 'taskbarFont', 'smallestReadableFont']
            settings = {}
            for k in font_keys:
                val = subprocess.run(['kreadconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', k], capture_output=True, text=True).stdout.strip()
                if val: settings[k] = val

            active_font = subprocess.run(['kreadconfig6', '--file', 'kdeglobals', '--group', 'WM', '--key', 'activeFont'], capture_output=True, text=True).stdout.strip()
            if active_font: settings['activeFont'] = active_font

            icons = subprocess.run(['kreadconfig6', '--file', 'kdeglobals', '--group', 'Icons', '--key', 'Theme'], capture_output=True, text=True).stdout.strip()
            style = subprocess.run(['kreadconfig6', '--file', 'kdeglobals', '--group', 'KDE', '--key', 'widgetStyle'], capture_output=True, text=True).stdout.strip()
            decor = subprocess.run(['kreadconfig6', '--file', 'kwinrc', '--group', 'org.kde.kdecoration2', '--key', 'library'], capture_output=True, text=True).stdout.strip()
            decor_theme = subprocess.run(['kreadconfig6', '--file', 'kwinrc', '--group', 'org.kde.kdecoration2', '--key', 'theme'], capture_output=True, text=True).stdout.strip()
            theme = subprocess.run(['kreadconfig6', '--file', 'plasmarc', '--group', 'Theme', '--key', 'name'], capture_output=True, text=True).stdout.strip()
            colorscheme = subprocess.run(['kreadconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', 'ColorScheme'], capture_output=True, text=True).stdout.strip()

            wm_keys = ['activeBackground', 'activeForeground', 'inactiveBackground', 'inactiveForeground']
            for k in wm_keys:
                val = subprocess.run(['kreadconfig6', '--file', 'kdeglobals', '--group', 'WM', '--key', k], capture_output=True, text=True).stdout.strip()
                if val: settings[f'wm_{k}'] = val

            with open(backup_file, 'w') as f:
                f.write(f"icons={icons}\nstyle={style}\ndecor={decor}\ndecor_theme={decor_theme}\ntheme={theme}\ncolorscheme={colorscheme}\n")
                for k, v in settings.items():
                    f.write(f"{k}={v}\n")

        # 4. Определяем цвета в зависимости от режима
        if mode == "light":
            new_theme = "breeze"
            new_colorscheme = "BreezeLight"
        elif mode == "dark":
            new_theme = "breeze-dark"
            new_colorscheme = "BreezeDark"
        else:  # mixed
            new_theme = "breeze-dark"
            new_colorscheme = "BreezeLight"

        # 5. Удаляем жестко заданные цвета заголовков
        wm_keys = ['activeBackground', 'activeForeground', 'inactiveBackground', 'inactiveForeground']
        for k in wm_keys:
            subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'WM', '--key', k, '--delete'])

        # 6. Применяем иконки и темы
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'Icons', '--key', 'Theme', papirus_theme_name])
        subprocess.run(['kwriteconfig6', '--file', 'plasmarc', '--group', 'Theme', '--key', 'name', new_theme])
        subprocess.run(['kwriteconfig6', '--file', 'kwinrc', '--group', 'org.kde.kdecoration2', '--key', 'library', 'org.kde.breeze'])
        subprocess.run(['kwriteconfig6', '--file', 'kwinrc', '--group', 'org.kde.kdecoration2', '--key', 'theme', 'Breeze'])

        # 7. Применяем цветовую схему (оставляем как было)
        res = subprocess.run(['plasma-apply-colorscheme', new_colorscheme], capture_output=True)
        if res.returncode != 0:
            subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', 'ColorScheme', new_colorscheme])

        # 7б. ВСЕГДА выставляем widgetStyle = Breeze (не только при сбое plasma-apply-colorscheme)
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'KDE', '--key', 'widgetStyle', 'Breeze'])

        # 8. Очистка кэша и перезапуск плазмы
        subprocess.run(['rm', '-f', os.path.expanduser('~/.cache/icon-cache.kcache')])
        subprocess.run(['kbuildsycoca6', '--noincremental'], capture_output=True)
        subprocess.run(['qdbus-qt6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure'], capture_output=True)
        self.restart_plasmashell()

        # 9. Обновляем индикаторы на кнопках
        self.update_theme_checkmarks()

        # 10. Принудительно переключаем тему программы под выбранный режим окон
        QApplication.instance().setStyleSheet(get_stylesheet(force_dark=(mode == "dark")))

    def on_rollback_modern_ui(self):
        config_dir = get_config_dir()
        backup_file = os.path.join(config_dir, 'ui_backup.txt')

        if not os.path.exists(backup_file):
            QMessageBox.warning(self, "Нет данных", "Файл с предыдущими настройками не найден.\nОткатывать нечего.")
            return

        # 1. Читаем старые настройки
        settings = {}
        with open(backup_file, 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    settings[k] = v

        # 2. Применяем обратно шрифты
        font_keys = ['font', 'menuFont', 'toolbarFont', 'taskbarFont', 'smallestReadableFont']
        for k in font_keys:
            if k in settings:
                subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', k, settings[k]])

        if 'activeFont' in settings:
            subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'WM', '--key', 'activeFont', settings['activeFont']])

        # Восстанавливаем жестко заданные цвета заголовков (если были)
        wm_keys = ['activeBackground', 'activeForeground', 'inactiveBackground', 'inactiveForeground']
        for k in wm_keys:
            if f'wm_{k}' in settings:
                subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'WM', '--key', k, settings[f'wm_{k}']])
            else:
                # Если в бэкапе нет, значит их не было, удаляем на всякий случай
                subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'WM', '--key', k, '--delete'])

        # 3. Применяем остальные настройки
        if settings.get('icons'):
            subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'Icons', '--key', 'Theme', settings['icons']])
        if settings.get('style'):
            subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'KDE', '--key', 'widgetStyle', settings['style']])
        if settings.get('decor'):
            subprocess.run(['kwriteconfig6', '--file', 'kwinrc', '--group', 'org.kde.kdecoration2', '--key', 'library', settings['decor']])
        if settings.get('decor_theme'):
            subprocess.run(['kwriteconfig6', '--file', 'kwinrc', '--group', 'org.kde.kdecoration2', '--key', 'theme', settings['decor_theme']])
        if settings.get('theme'):
            subprocess.run(['kwriteconfig6', '--file', 'plasmarc', '--group', 'Theme', '--key', 'name', settings['theme']])

        # Восстанавливаем цветовую схему
        if settings.get('colorscheme'):
            res = subprocess.run(['plasma-apply-colorscheme', settings['colorscheme']], capture_output=True)
            if res.returncode != 0:
                subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', 'ColorScheme', settings['colorscheme']])

        # 4. Очищаем кэш иконок и пересобираем кэш KDE
        subprocess.run(['rm', '-f', os.path.expanduser('~/.cache/icon-cache.kcache')])
        subprocess.run(['kbuildsycoca6', '--noincremental'], capture_output=True)
        subprocess.run(['qdbus-qt6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure'], capture_output=True)

        # 5. Удаляем файл бэкапа, чтобы следующее применение сохранило новое состояние
        if os.path.exists(backup_file):
            os.remove(backup_file)

        # 6. Перезапускаем плазму, чтобы всё применилось
        self.restart_plasmashell()

        QMessageBox.information(self, "Готово", "Предыдущие настройки интерфейса восстановлены.\nПанель была перезапущена.")

    def create_fixes_page(self):
        cards = []
        cards.append(SimpleActionCard("Установка кодека openh264 для Flatpak (без VPN)", "Устанавливает кодек openh264 для Flatpak через stplr, для этого VPN не нужен.", "21_install_openh264_action.sh"))
        cards.append(SimpleActionCard("Включить 3D-ускорение для Google Chrome (Flatpak)", "Включает аппаратное ускорение\nдля Google Chrome из Flatpak.", "16_flatpak_chrome_3d_action.sh"))
        cards.append(SimpleActionCard("Разрешить загрузку тем и виджетов из сети", "Включает Get Hot New Stuff (ghns) в KDE", "17_enable_ghns_action.sh"))
        cards.append(SimpleActionCard("Добавить себя в группы dialout, lp, adbusers + доступ к USBasp", "Добавляет текущего пользователя в группы \nдля доступа к USB и правила udev для USBasp устройств", "08_add_groups_action.sh"))

        cards.append(ActionCard("Действия в контекстном меню Dolphin", "Добавляет в контекстное меню Dolphin два пункта:\n«Открыть как текст» — открывает файл в редакторе по умолчанию,\n«Сделать исполняемым» — выставляет права на выполнение (chmod +x).\n\nПункты выводятся в корень контекстного меню.", "29_add_actions_dolphin_action.sh", "29_add_actions_dolphin_rollback.sh"))
        cards.append(ActionCard("Установка virtualbox со всеми дополнениями", "Установка virtualbox со всеми дополнениями, отключение KVM.\nОткат удаляет virtualbox и возвращает KVM обратно.", "24_install_virtualbox_action.sh", "24_install_virtualbox_rollback.sh"))

        flatpak_card = ActionCard("Установка Flatpak", "Устанавливает Flatpak, плагин для Discover,подключает репозиторий Flathub.\nВ случае удаления Flatpak будут удалены и все приложения из него.", "10_install_flatpak_action.sh", "10_install_flatpak_rollback.sh")
        cards.append(flatpak_card)

        cards.append(ActionCard("Установка или обновление eepm", "Устанавливает eepm, epmgpi, eepm-play-gui, \nобновляет eepm с сайта etersoft.", "06_install_eepm_action.sh", "06_install_eepm_rollback.sh"))
        cards.append(ActionCard("Установка stplr/aides", "Будут установлены stplr, плагин для Discover и репозиторий aides.\nВажно! В Discover пропадет возможность установки Google Chrome из Flatpak,\nвместо этого появится Google Chrome из Stapler! При необходимости можно удалить stplr по кнопке Откат,\nустановить Chrome из Flatpak, а потом установить stplr/aides.", "20_install_stplr_action.sh", "20_install_stplr_rollback.sh"))

        home_access_card = ActionCard("Доступ для flatpak ко всему домашнему каталогу на чтение", "Необходимо для перетаскивания файлов на окна flatpak-приложений.\n\nДетальная настройка прав:\nПараметры системы → Права доступа приложений →\n→ выбрать приложение → кнопка \"Управление параметрами flatpak\"", "11_flatpak_home_access_action.sh", "11_flatpak_home_access_rollback.sh")
        cards.append(home_access_card)

        cards.append(ActionCard("Исправить поведение индикатора копирования файлов", "Исправляет ситуацию, когда запись на флешку закончена\nпо индикатору копирования, а флешка еще долго не отмонтируется.", "12_fix_copy_indicator_action.sh", "12_fix_copy_indicator_rollback.sh"))
        cards.append(ActionCard("Исправить конфликт Wi-Fi и Bluetooth", "Отключает глубокий сон Wi-Fi-драйвера Realtek (LPS Deep).\nПомогает, если Bluetooth-аудио периодически прерывается\nпри активном Wi-Fi (особенно на чипах RTL8821CE).\nНемного увеличивает энергопотребление.\n\nТребуется перезагрузка.", "32_fix_bluetooth_wifi_coex_action.sh", "32_fix_bluetooth_wifi_coex_rollback.sh"))
        cards.append(ActionCard("Показ миниатюр для 3D-файлов (STL, FCstd)", "Включается создание миниатюр для файлов .stl, .FCstd\nдля отображения в файлменеджере в режиме значков,\nдля программ 3D-моделирования FreeCAD, слайсеров и т. д.", "14_thumbnails_3d_action.sh", "14_thumbnails_3d_rollback.sh"))
        cards.append(ActionCard("Показ миниатюр для файлов .dwg (AutoCAD)", "Включается создание миниатюр для файлов .dwg (AutoCAD).\nБудет установлен NConvert, бесплатен для некоммерческого\nиспользования.", "15_thumbnails_dwg_action.sh", "15_thumbnails_dwg_rollback.sh"))

        codec_card = next((c for c in cards if hasattr(c, 'script_name') and c.script_name == "21_install_openh264_action.sh"), None)
        def on_flatpak_toggled(state):
            if state == Qt.CheckState.Checked.value:
                if codec_card:
                    codec_card.install_cb.blockSignals(True)
                    codec_card.install_cb.setChecked(True)
                    codec_card.install_cb.blockSignals(False)
                    codec_card.update_style('orange')
                home_access_card.install_cb.blockSignals(True)
                home_access_card.install_cb.setChecked(True)
                home_access_card.install_cb.blockSignals(False)
                home_access_card.update_style('orange')
        flatpak_card.install_cb.stateChanged.connect(on_flatpak_toggled)

        # Замедление мыши по кнопке "вперед" (перед samba)
        cards.append(ActionCard(
            "Замедление мыши по кнопке 'вперед'",
            "Позволяет переключать скорость мыши для удобной работы в CAD-программах.\n"
            "Нажатие доп. кнопки 'Вперёд' переключает между обычным и замедленным режимом.\n"
            "Тачпад не затрагивается.\n\n"
            "Требуется выйти из сеанса и войти снова для применения изменений.",
            "33_mouse-speed_action.sh",
            "33_mouse-speed_rollback.sh"
        ))

        cards.append(ActionCard(
            "Исправить неправильное определение USB-принтера",
            "Помогает, если принтер подключён по USB, но система его не видит\n"
            "или определяет неправильно (как сетевое устройство).\n\n"
            "На принтеры по Wi-Fi или сетевому кабелю это не влияет.\n"
            "Но если к компьютеру подключены другие USB-принтеры или МФУ,\n"
            "которые работают без отдельного драйвера (режим driverless),\n"
            "их определение и печать могут нарушиться — в этом случае\n"
            "используйте кнопку «Откат».\n\n"
            "После применения переподключите USB-кабель принтера\n"
            "или перезагрузите компьютер.\n\n"
            "Кнопка «Откат» возвращает всё как было.",
            "34_mask_ippusb_action.sh",
            "34_mask_ippusb_rollback.sh"
        ))

        cards.append(ActionCard("Включить локальную сеть (samba)", "Включает в автозапуск сервисы smb и nmb для обеспечения\nработы локальной сети с протоколом SMB.\n\nПакеты samba и samba-client должны быть установлены.", "22_enable_samba_action.sh", "22_enable_samba_rollback.sh"))
        return CategoryPage(cards)

    def create_maintenance_page(self):
        cards = []
        cards.append(MirrorCard())
        if subprocess.run(['rpm', '-q', 'flatpak'], capture_output=True).returncode == 0:
            cards.append(FlathubMirrorCard())
        cards.append(SimpleActionCard("Установка рекомендованных пакетов", f"Устанавливает пакеты из списка {get_packages_file_path()}\nСписок можно редактировать через меню в верхнем левом углу окна приложения", "07_install_packages_action.sh"))
        cards.append(SimpleActionCard("Обновление / удаление ядер", "Установка новых и удаление неиспользуемых ядер.\nВнимательно следите за выводом в терминале! ", "23_update_kernel_action.sh"))
        cards.append(SimpleActionCard("Ремонт apt-get при ошибках", "apt-get dedup && pm --rebuilddb", "01_repair_apt_action.sh"))
        cards.append(SimpleActionCard("Исправление ошибки с прокси в Discover", "Пересоздание кэша packagekit.\nУстраняет ошибку, когда Discover не подключается к сети\nпосле удаления локального прокси.", "09_fix_discover_proxy_action.sh"))

        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(12, 10, 12, 5)

        title_label = QLabel("<b>Регулярное обслуживание системы</b>")
        title_label.setStyleSheet("font-size: 14px; color: palette(text);")
        title_layout.addWidget(title_label)

        # Отступ 5 пикселей и чекбокс
        title_layout.addSpacing(5)

        self.maint_master_cb = QCheckBox()
        self.maint_master_cb.setTristate(True)
        self.maint_master_cb.setToolTip("Выбрать / отменить все три действия ниже")
        title_layout.addWidget(self.maint_master_cb)

        title_layout.addStretch() # Распорка прижимает всё влево

        title_widget.setLayout(title_layout)
        cards.append(title_widget)

        card_update_sys = SimpleActionCard(
            "Обновление системы и программ из всех источников",
            "Будет обновлена система из репозитория (rpm-пакеты),\nа также обновятся и другие установленные в системе источники\nи программы из них.",
            "05_update_system_action.sh"
        )
        cards.append(card_update_sys)

        card_clean_cache = SimpleActionCard(
            "Очистка кэша",
            "Очистка кэшей: в домашнем каталоге, для Flatpak-приложений,\nаккуратную очистку системного кэша, удаление старых журналов\nи сжатие до размера 100 МБ максимум, очистку кэша пакетов\n(без применения небезопасной опции autoremove),\nудаление неиспользуемых рантаймов Flatpak,\nудаление старых ядер.",
            "95_clean_cache_action.sh"
        )
        cards.append(card_clean_cache)

        card_clean_orphan = SimpleActionCard(
            "Очистка данных удалённых Flatpak-приложений",
            "Находит в ~/.var/app папки приложений Flatpak, которых больше нет в системе.\n"
            "Показывает список с именами и спрашивает подтверждение.\n"
            "Папки перемещаются в корзину, откуда их можно восстановить,\n"
            "если приложение понадобится снова.",
            "96_clean_orphan_flatpak_data_action.sh"
        )
        cards.append(card_clean_orphan)

        self.maint_target_cards = [card_update_sys, card_clean_cache, card_clean_orphan]
        for c in self.maint_target_cards:
            c.install_cb.stateChanged.connect(self.update_maint_master_state)
        self.maint_master_cb.clicked.connect(self.on_maint_master_clicked)

        return CategoryPage(cards)

def run():
    # Удаляем устаревший theme.conf (ручной выбор темы больше не используется)
    try:
        legacy = os.path.expanduser('~/.config/alt-kde-helper/theme.conf')
        if os.path.exists(legacy):
            os.remove(legacy)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyleSheet(get_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
