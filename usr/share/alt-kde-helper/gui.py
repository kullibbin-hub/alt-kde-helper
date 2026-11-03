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
from PyQt6.QtGui import QDesktopServices, QIcon, QCloseEvent, QAction
from config import (
    get_stylesheet, get_scripts_dir, get_state_dir, get_actions_dir,
    clear_actions_dir, get_help_path, get_version,
    load_theme_setting, save_theme_setting, is_dark_theme
)

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

        self.process = subprocess.Popen(
            ['konsole', '--new-tab', '--title', 'Применение изменений', '-e', 'bash', '-c', cmd],
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
        self.btn_editable_tray.setMinimumHeight(50)
        self.btn_editable_tray.setToolTip("Позволяет перемещать значки громкости, раскладки клавиатуры,\nподключенных устройств в режиме редактирования панели.\n\nДобавленные вручную виджеты будут удалены,\nнадо будет добавить их заново.")
        content_layout.addWidget(self.btn_editable_tray)

        self.btn_save_panel = QPushButton("Сохранить настройки виджетов панели")
        self.btn_save_panel.setProperty("class", "BottomButton")
        self.btn_save_panel.setMinimumHeight(50)
        self.btn_save_panel.setToolTip("Сохраняет текущие настройки панели и виджетов\nв архив tar.gz. Выберите путь и имя файла.")
        content_layout.addWidget(self.btn_save_panel)

        self.btn_load_panel = QPushButton("Загрузить настройки виджетов панели")
        self.btn_load_panel.setProperty("class", "BottomButton")
        self.btn_load_panel.setMinimumHeight(50)
        self.btn_load_panel.setToolTip("Загружает настройки панели из ранее сохранённого\nархива tar.gz. Выберите файл архива.")
        content_layout.addWidget(self.btn_load_panel)

        self.btn_reset_panel = QPushButton("Вернуть расположение виджетов по умолчанию")
        self.btn_reset_panel.setProperty("class", "BottomButton")
        self.btn_reset_panel.setMinimumHeight(50)
        self.btn_reset_panel.setToolTip("Удаляет текущие настройки панели и восстанавливает\nзаводские настройки по умолчанию.\n\nДобавленные вручную виджеты будут удалены.")
        content_layout.addWidget(self.btn_reset_panel)

        # --- Визуальный разделитель ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: palette(mid); margin-top: 10px; margin-bottom: 10px;")
        content_layout.addWidget(line)

        # --- Блок 2: Дополнительные настройки ---
        content_layout.addSpacing(15)
        extra_title = QLabel("<b>Дополнительные настройки</b>")
        extra_title.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        content_layout.addWidget(extra_title)

        # Список карточек для этой страницы (чтобы MainWindow мог их найти)
        self.cards = []

        # 1. Значки Papirus
        card_papirus = SimpleActionCard(
            "Установка цветных значков papirus",
            "Будут установлены значки papirus-remix-icon-theme с разными цветами папок.\nУстановка может занимать несколько минут, из-за большого количества маленьких файлов,\nнаберитесь терпения.",
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
            "Устанавливает базовый размер шрифта — 10",
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
        self.resize(800, 700)

        clear_actions_dir()

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_panel = QWidget()
        left_panel.setFixedWidth(140)
        left_panel.setAutoFillBackground(True)

        from PyQt6.QtGui import QPalette
        pal = left_panel.palette()
        pal.setColor(QPalette.ColorRole.Window, pal.color(QPalette.ColorRole.Base))
        left_panel.setPalette(pal)

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
        menu_container.setAutoFillBackground(True)
        palette = menu_container.palette()
        palette.setColor(menu_container.backgroundRole(), palette.color(QPalette.ColorRole.Window))
        menu_container.setPalette(palette)

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

        self.tab_btn_maintenance = QPushButton("Обслуживание")
        self.tab_btn_maintenance.setProperty("class", "TabButtonActive")
        self.tab_btn_maintenance.setCheckable(True)
        self.tab_btn_maintenance.setChecked(True)
        self.tab_btn_maintenance.setMinimumHeight(50)
        self.tab_btn_maintenance.clicked.connect(lambda: self.switch_tab(0))
        left_panel_layout.addWidget(self.tab_btn_maintenance)

        self.tab_btn_fixes = QPushButton("Настройки")
        self.tab_btn_fixes.setProperty("class", "TabButton")
        self.tab_btn_fixes.setCheckable(True)
        self.tab_btn_fixes.setMinimumHeight(50)
        self.tab_btn_fixes.clicked.connect(lambda: self.switch_tab(1))
        left_panel_layout.addWidget(self.tab_btn_fixes)

        self.tab_btn_appearance = QPushButton("Оформление")
        self.tab_btn_appearance.setProperty("class", "TabButton")
        self.tab_btn_appearance.setCheckable(True)
        self.tab_btn_appearance.setMinimumHeight(50)
        self.tab_btn_appearance.clicked.connect(lambda: self.switch_tab(2))
        left_panel_layout.addWidget(self.tab_btn_appearance)

        left_panel_layout.addStretch()
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

        self.stack_layout.addWidget(self.maintenance_page)
        self.stack_layout.addWidget(self.fixes_page)
        self.stack_layout.addWidget(self.appearance_page)

        self.fixes_page.setVisible(False)
        self.appearance_page.setVisible(False)

        self.stack.setLayout(self.stack_layout)
        right_layout.addWidget(self.stack, 1)

        bottom_layout = QHBoxLayout()
        line_h = QFrame()
        line_h.setFrameShape(QFrame.Shape.HLine)
        line_h.setFrameShadow(QFrame.Shadow.Sunken)
        line_h.setFixedHeight(1)
        right_layout.addWidget(line_h)

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

        menu.exec(self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height())))

    def switch_tab(self, index):
        self.maintenance_page.setVisible(index == 0)
        self.fixes_page.setVisible(index == 1)
        self.appearance_page.setVisible(index == 2)

        self.tab_btn_maintenance.setProperty("class", "TabButtonActive" if index == 0 else "TabButton")
        self.tab_btn_fixes.setProperty("class", "TabButtonActive" if index == 1 else "TabButton")
        self.tab_btn_appearance.setProperty("class", "TabButtonActive" if index == 2 else "TabButton")

        for btn in [self.tab_btn_maintenance, self.tab_btn_fixes, self.tab_btn_appearance]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.apply_btn.setEnabled(True)

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
                        shutil.copy2(script_src, action_path)
                if hasattr(card, 'rollback_cb') and card.rollback_cb.isChecked():
                    script_src = os.path.join(scripts_dir, card.rollback_script_name)
                    action_path = os.path.join(actions_dir, card.rollback_script_name)
                    if os.path.exists(script_src) and not os.path.exists(action_path):
                        shutil.copy2(script_src, action_path)

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
                        shutil.copy2(script_src, action_path)

            update_script = "30_update_appimage_action.sh"
            script_src = os.path.join(scripts_dir, update_script)
            action_path = os.path.join(actions_dir, update_script)
            if os.path.exists(script_src) and not os.path.exists(action_path):
                shutil.copy2(script_src, action_path)

        mirror_card = self.get_mirror_card()
        if mirror_card:
            selected_script = mirror_card.get_selected_mirror_script()
            if selected_script:
                script_src = os.path.join(scripts_dir, selected_script)
                action_path = os.path.join(actions_dir, selected_script)
                if os.path.exists(script_src) and not os.path.exists(action_path):
                    shutil.copy2(script_src, action_path)

        flathub_mirror_card = self.get_flathub_mirror_card()
        if flathub_mirror_card:
            selected_script = flathub_mirror_card.get_selected_mirror_script()
            if selected_script:
                script_src = os.path.join(scripts_dir, selected_script)
                action_path = os.path.join(actions_dir, selected_script)
                if os.path.exists(script_src) and not os.path.exists(action_path):
                    shutil.copy2(script_src, action_path)

        action_files = [f for f in os.listdir(actions_dir) if f.endswith('.sh') and f != '99_final.sh']
        if not action_files:
            QMessageBox.information(self, "Нет действий", "Нет действий для применения.")
            return

        final_script_src = os.path.join(scripts_dir, '99_final.sh')
        final_script_dst = os.path.join(actions_dir, '99_final.sh')
        if os.path.exists(final_script_src) and not os.path.exists(final_script_dst):
            shutil.copy2(final_script_src, final_script_dst)

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
                shutil.copy2(final_script_src, final_script_dst)
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
            "<a href='https://github.com/kullibbin-hub/alt-kde-helper'>GitHub</a>")

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

        process = subprocess.Popen(['konsole', '--new-tab', '--title', 'Установка обновления', '-e', 'bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()

        if process.returncode == 0:
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
        subprocess.run(['killall', 'plasmashell'], capture_output=True)
        subprocess.Popen(['bash', '-c', 'plasmashell --replace >/dev/null 2>&1 & disown'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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

        cards.append(SimpleActionCard("Восстановление работы USB-принтера", "Переустанавливает пакет ipp-usb.\nПомогает, если USB-принтер перестал определяться\nи вместо него создаётся принтер driverless.\n\nТребуется подключение к интернету.\nПосле выполнения может потребоваться переподключить USB-кабель.", "34_reinstall_ippusb_action.sh"))

        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 10, 0, 5)
        title_label = QLabel("<b>Текущее обслуживание системы</b>")
        title_label.setStyleSheet("font-size: 14px; color: palette(text);")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_widget.setLayout(title_layout)
        cards.append(title_widget)

        cards.append(SimpleActionCard("Обновление системы и программ из всех источников", "Будет обновлена система из репозитория (rpm-пакеты),\nа также обновятся и другие установленные в системе источники\nи программы из них.", "05_update_system_action.sh"))
        cards.append(SimpleActionCard("Очистка кэша", "Очистка кэшей: в домашнем каталоге, для Flatpak-приложений,\nаккуратную очистку системного кэша, удаление старых журналов\nи сжатие до размера 100 МБ максимум, очистку кэша пакетов\n(без применения небезопасной опции autoremove),\nудаление неиспользуемых рантаймов Flatpak,\nудаление старых ядер.", "95_clean_cache_action.sh"))
        return CategoryPage(cards)

def run():
    app = QApplication(sys.argv)
    saved = load_theme_setting()
    if saved is not None:
        app.setStyleSheet(get_stylesheet(force_dark=saved))
    else:
        app.setStyleSheet(get_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
