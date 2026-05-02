# gui.py - графический интерфейс Alt KDE Helper

import sys
import os
import shutil
import subprocess
import glob
import signal
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QFrame,
    QScrollArea, QMessageBox, QPushButton, QButtonGroup, QDialog, QApplication,
    QMenu, QRadioButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QPoint, QEvent
from PyQt6.QtGui import QDesktopServices, QIcon, QCloseEvent, QAction

from config import (
    get_stylesheet, get_scripts_dir, get_state_dir, get_actions_dir,
    clear_actions_dir, get_help_path, get_version,
    load_theme_setting, save_theme_setting, is_dark_theme
)


def get_current_version():
    """Возвращает текущую версию программы из version.txt"""
    try:
        # Пробуем прочитать из системного файла
        version_file = '/usr/share/doc/alt-kde-helper/version.txt'
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
    except:
        pass
    # fallback
    return '1.2.2'


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
    """
    Проверяет наличие файла списка пакетов для текущей версии.
    Если файла нет, показывает диалог миграции (при обновлении)
    или просто копирует default (при первом запуске).
    """
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)

    current_version = get_current_version()
    target_file = get_packages_file_path()
    default_file = get_default_packages_path()

    # Если файл для текущей версии уже существует — просто возвращаем его
    if os.path.exists(target_file):
        return target_file

    # Ищем старые файлы с другими версиями
    old_files = glob.glob(os.path.join(config_dir, 'user_packages_*.txt'))
    # Отфильтровываем .old.txt файлы
    old_files = [f for f in old_files if not f.endswith('.old.txt')]

    # Если нет старых файлов — первый запуск программы
    if not old_files:
        if os.path.exists(default_file):
            shutil.copy2(default_file, target_file)
        else:
            # Если нет default — создаём пустой файл
            open(target_file, 'w').close()
        return target_file

    # Есть старые файлы — значит, это обновление программы
    # Сортируем по имени (версия в имени) и берём самый новый (последний)
    old_files.sort()
    latest_old_file = old_files[-1]

    # Показываем диалог выбора
    dialog = QDialog(parent) if parent else QDialog()
    dialog.setWindowTitle("Обновление списка пакетов")
    dialog.setMinimumWidth(550)

    layout = QVBoxLayout()

    # Заголовок
    title = QLabel(f"<b>Обнаружена новая версия программы ({current_version})</b>")
    title.setWordWrap(True)
    layout.addWidget(title)

    layout.addSpacing(10)

    # Пояснение
    info = QLabel("В новой версии изменён и дополнен список рекомендуемых пакетов.")
    info.setWordWrap(True)
    layout.addWidget(info)

    layout.addSpacing(15)

    # Радиокнопки
    keep_radio = QRadioButton("Оставить мой текущий список")
    keep_radio.setToolTip("Ваши личные изменения сохранятся, новые пакеты из обновления добавлены не будут")

    replace_radio = QRadioButton("Заменить список новым (рекомендуется)")
    replace_radio.setToolTip("Вы получите актуальный список пакетов для установки")
    replace_radio.setChecked(True)  # по умолчанию выбран

    layout.addWidget(keep_radio)
    layout.addWidget(replace_radio)

    layout.addSpacing(15)

    # Путь к папке со старыми файлами (кликабельная ссылка)
    folder_link = QLabel(
        f'📁 <b>Ваш старый список не будет удалён.</b><br>'
        f'Он останется в папке: <a href="file://{config_dir}">{config_dir}</a>'
    )
    folder_link.setWordWrap(True)
    folder_link.setOpenExternalLinks(True)
    layout.addWidget(folder_link)

    layout.addSpacing(20)

    # Кнопки
    button_layout = QHBoxLayout()
    ok_btn = QPushButton("Продолжить")
    cancel_btn = QPushButton("Отмена")
    button_layout.addStretch()
    button_layout.addWidget(ok_btn)
    button_layout.addWidget(cancel_btn)
    layout.addLayout(button_layout)

    dialog.setLayout(layout)

    def on_ok():
        dialog.done(1)

    def on_cancel():
        dialog.done(0)

    ok_btn.clicked.connect(on_ok)
    cancel_btn.clicked.connect(on_cancel)

    result = dialog.exec()

    if result == 0:  # Отмена
        # Пользователь отменил — выходим, файл не создаём
        return None

    if replace_radio.isChecked():
        # Заменить новым списком
        if os.path.exists(default_file):
            shutil.copy2(default_file, target_file)
        else:
            open(target_file, 'w').close()
    else:
        # Оставить текущий список — копируем старый файл в новый с текущей версией
        shutil.copy2(latest_old_file, target_file)

    return target_file


class ActionWorker(QThread):
    """Поток для выполнения действий в терминале"""
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
        """Принудительно завершает терминал"""
        if self.terminal_pid:
            try:
                os.kill(self.terminal_pid, signal.SIGTERM)
            except:
                pass
        elif self.process and self.process.poll() is None:
            self.process.terminate()


class ActionCard(QFrame):
    """Карточка с двумя чекбоксами для действия с откатом"""
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
    """Простая карточка с одним чекбоксом для действия без отката"""
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
    """Карточка для выбора зеркала (радиокнопки)"""
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

        # Радиокнопка "Не менять"
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
            state_file = os.path.join(state_dir, script_name)
            if os.path.exists(state_file):
                active_script = script_name
                break

        # Сбрасываем стили описаний
        for script_name, (radio, desc_label) in self.radio_buttons.items():
            desc_label.setProperty("class", "Description")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
        self.none_label.setProperty("class", "Description")
        self.none_label.style().unpolish(self.none_label)
        self.none_label.style().polish(self.none_label)

        # ВСЕГДА устанавливаем радиокнопку "Не менять" (никогда не выбираем зеркало автоматически)
        self.none_radio.blockSignals(True)
        self.none_radio.setChecked(True)
        self.none_radio.blockSignals(False)

        # Если есть активный флаг — подсвечиваем соответствующую карточку зелёным
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
        if not checked:
            return

        mirror_scripts = list(self.radio_buttons.keys())

        selected_script = None
        for script_name, (r, desc_label) in self.radio_buttons.items():
            if r == radio:
                selected_script = script_name
                break

        # Снимаем выделение со всех карточек
        for script_name, (r, lbl) in self.radio_buttons.items():
            if script_name != selected_script:
                state_file = os.path.join(get_state_dir(), script_name)
                if os.path.exists(state_file):
                    lbl.setProperty("class", "DescriptionGreen")
                else:
                    lbl.setProperty("class", "Description")
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)

        if selected_script:
            # Выделяем выбранный пункт оранжевым
            _, desc_label = self.radio_buttons[selected_script]
            desc_label.setProperty("class", "DescriptionOrange")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
            self.none_label.setProperty("class", "Description")
        else:
            # Выбрано "Не менять"
            any_flag = any(os.path.exists(os.path.join(get_state_dir(), sn)) for sn in mirror_scripts)
            if any_flag:
                self.none_label.setProperty("class", "Description")
            else:
                self.none_label.setProperty("class", "DescriptionGreen")
            self.none_label.style().unpolish(self.none_label)
            self.none_label.style().polish(self.none_label)

        # Обновляем стиль none_label
        self.none_label.style().unpolish(self.none_label)
        self.none_label.style().polish(self.none_label)

    def set_fast_mirror(self, enable):
        fast_script = "02_repo_fast_mirror_action.sh"
        if fast_script in self.radio_buttons:
            radio, desc_label = self.radio_buttons[fast_script]
            if enable:
                if not radio.isChecked():
                    radio.setChecked(True)
            else:
                if radio.isChecked():
                    self.none_radio.setChecked(True)

    def is_fast_mirror_selected(self):
        fast_script = "02_repo_fast_mirror_action.sh"
        if fast_script in self.radio_buttons:
            radio, _ = self.radio_buttons[fast_script]
            return radio.isChecked()
        return False

    def get_selected_mirror_script(self):
        """Возвращает имя выбранного скрипта зеркала или None"""
        if self.none_radio.isChecked():
            return None
        for script_name, (radio, desc_label) in self.radio_buttons.items():
            if radio.isChecked():
                return script_name
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alt KDE Helper")
        self.setObjectName("alt-kde-helper")
        self.setMinimumSize(800, 640)
        self.resize(800, 640)

        clear_actions_dir()

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Левая панель с кнопками категорий и меню
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

        # Кнопка-меню с системной иконкой KDE
        self.menu_button = QPushButton()
        self.menu_button.setIcon(QIcon.fromTheme("application-menu"))
        self.menu_button.setIconSize(self.menu_button.sizeHint())
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
        left_panel_layout.addWidget(self.menu_button, alignment=Qt.AlignmentFlag.AlignLeft)

        left_panel_layout.addSpacing(20)

        # Кнопки категорий
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

        left_panel_layout.addStretch()
        left_panel.setLayout(left_panel_layout)

        # Правая часть (контент + кнопки внизу)
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Стек страниц
        self.stack = QWidget()
        self.stack_layout = QVBoxLayout()
        self.stack_layout.setContentsMargins(0, 0, 0, 0)

        self.maintenance_page = self.create_maintenance_page()
        self.fixes_page = self.create_fixes_page()

        self.stack_layout.addWidget(self.maintenance_page)
        self.stack_layout.addWidget(self.fixes_page)
        self.fixes_page.setVisible(False)

        self.stack.setLayout(self.stack_layout)
        right_layout.addWidget(self.stack, 1)

        # Нижняя панель с кнопками
        bottom_layout = QHBoxLayout()

        # Добавляем разделительную полосу между контентом и нижней панелью
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

        # Добавляем разделительную полосу между левой панелью и правой частью
        line_v = QFrame()
        line_v.setFrameShape(QFrame.Shape.VLine)
        line_v.setFrameShadow(QFrame.Shadow.Sunken)
        line_v.setFixedWidth(1)
        main_layout.insertWidget(1, line_v)

        central.setLayout(main_layout)

        self.help_dialog = None
        self.recommended_state = False
        self.current_worker = None

        self.recommended_scripts = [
            "12_fix_copy_indicator_action.sh",
            "13_increase_fonts_action.sh",
            "17_enable_ghns_action.sh",
            "08_add_groups_action.sh",
            "05_update_system_action.sh",
            "95_clean_cache_action.sh",
            "06_install_eepm_action.sh",
            "07_install_packages_action.sh"
        ]

        # Запускаем скрипт проверки состояния системы после создания страниц
        self.run_check_state()

        # Создаём/обновляем список пакетов с учётом версии
        ensure_packages_file(self)

        # Обновляем состояние карточек после проверки
        for card in self.get_all_cards():
            if hasattr(card, 'load_state'):
                card.load_state()

    def showEvent(self, event):
        """Переприменяем стили при первом показе окна"""
        super().showEvent(event)
        # Принудительно обновляем стили после того, как окно появилось
        saved = load_theme_setting()
        if saved is not None:
            QApplication.instance().setStyleSheet(get_stylesheet(force_dark=saved))
        else:
            QApplication.instance().setStyleSheet(get_stylesheet())


    def event(self, event):
        if event.type() == QEvent.Type.ApplicationPaletteChange:
            # Тема оформления изменилась — обновляем стили с учётом сохранённой настройки
            saved = load_theme_setting()
            if saved is not None:
                # Если пользователь явно выбрал тему, используем её
                QApplication.instance().setStyleSheet(get_stylesheet(force_dark=saved))
            else:
                # Иначе автоопределение
                QApplication.instance().setStyleSheet(get_stylesheet())
            return True
        return super().event(event)

    def run_check_state(self):
        """Запускает скрипт проверки состояния системы"""
        check_state_script = os.path.join(get_scripts_dir(), 'check_state.sh')
        if os.path.exists(check_state_script):
            try:
                subprocess.run([check_state_script], check=False)
            except Exception as e:
                print(f"Ошибка при запуске check_state.sh: {e}")

    def show_menu(self):
        """Показывает меню"""
        menu = QMenu(self)

        help_action = QAction("Справка", self)
        help_action.triggered.connect(self.show_help)
        menu.addAction(help_action)
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        check_update_action = QAction("Проверить обновление", self)
        check_update_action.triggered.connect(self.check_for_updates)
        menu.addAction(check_update_action)

        menu.addSeparator()

        edit_packages_action = QAction("Редактировать список пакетов", self)
        edit_packages_action.triggered.connect(self.edit_packages_list)
        menu.addAction(edit_packages_action)

        open_folder_action = QAction("Открыть папку со списком пакетов", self)
        open_folder_action.triggered.connect(self.open_packages_folder)
        menu.addAction(open_folder_action)

        reset_packages_action = QAction("Восстановить список пакетов по умолчанию", self)
        reset_packages_action.triggered.connect(self.reset_packages_list)
        menu.addAction(reset_packages_action)

        menu.addSeparator()

        # Пункт переключения темы
        theme_action = QAction("Тёмная тема", self)
        theme_action.setCheckable(True)
        saved = load_theme_setting()
        if saved is None:
            # Не задано — определяем автоматически
            theme_action.setChecked(is_dark_theme())
        else:
            theme_action.setChecked(saved)
        theme_action.triggered.connect(self.toggle_theme)
        menu.addAction(theme_action)

        menu.exec(self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height())))

    def toggle_theme(self, checked):
        """Переключает тему (checked = True — тёмная, False — светлая)"""
        save_theme_setting(checked)
        QApplication.instance().setStyleSheet(get_stylesheet(force_dark=checked))

    def closeEvent(self, event: QCloseEvent):
        if hasattr(self, 'maintenance_page'):
            self.maintenance_page._closing = True
        if hasattr(self, 'fixes_page'):
            self.fixes_page._closing = True

        if hasattr(self, 'current_worker') and self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate_terminal()
            self.current_worker.quit()
            self.current_worker.wait(2000)
        event.accept()

    def switch_tab(self, index):
        self.maintenance_page.setVisible(index == 0)
        self.fixes_page.setVisible(index == 1)
        self.tab_btn_maintenance.setChecked(index == 0)
        self.tab_btn_fixes.setChecked(index == 1)

        self.tab_btn_maintenance.setProperty("class", "TabButtonActive" if index == 0 else "TabButton")
        self.tab_btn_fixes.setProperty("class", "TabButtonActive" if index == 1 else "TabButton")

        self.tab_btn_maintenance.style().unpolish(self.tab_btn_maintenance)
        self.tab_btn_maintenance.style().polish(self.tab_btn_maintenance)
        self.tab_btn_fixes.style().unpolish(self.tab_btn_fixes)
        self.tab_btn_fixes.style().polish(self.tab_btn_fixes)

    def get_all_cards(self):
        cards = []
        if hasattr(self.maintenance_page, 'cards'):
            cards.extend(self.maintenance_page.cards)
        if hasattr(self.fixes_page, 'cards'):
            cards.extend(self.fixes_page.cards)
        return cards

    def get_mirror_card(self):
        for card in self.get_all_cards():
            if isinstance(card, MirrorCard):
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

        # Собираем скрипты из Обслуживания
        for card in self.maintenance_page.cards:
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

        # Собираем скрипты из Настроек
        for card in self.fixes_page.cards:
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
        update_system_script = "05_update_system_action.sh"

        for card in self.maintenance_page.cards:
            if hasattr(card, 'script_name') and card.script_name == update_system_script:
                if hasattr(card, 'install_cb') and card.install_cb.isChecked():
                    update_system_checked = True
                break

        if update_system_checked:
            if subprocess.run("rpm -q eepm", shell=True, capture_output=True).returncode == 0:
                update_script = "06_update_eepm_action.sh"
                script_src = os.path.join(scripts_dir, update_script)
                action_path = os.path.join(actions_dir, update_script)
                if os.path.exists(script_src) and not os.path.exists(action_path):
                    shutil.copy2(script_src, action_path)

            if subprocess.run("rpm -q flatpak", shell=True, capture_output=True).returncode == 0:
                update_script = "10_update_flatpak_action.sh"
                script_src = os.path.join(scripts_dir, update_script)
                action_path = os.path.join(actions_dir, update_script)
                if os.path.exists(script_src) and not os.path.exists(action_path):
                    shutil.copy2(script_src, action_path)

            if subprocess.run("rpm -q stplr", shell=True, capture_output=True).returncode == 0:
                update_script = "20_update_stplr_action.sh"
                script_src = os.path.join(scripts_dir, update_script)
                action_path = os.path.join(actions_dir, update_script)
                if os.path.exists(script_src) and not os.path.exists(action_path):
                    shutil.copy2(script_src, action_path)

        mirror_card = None
        for card in self.maintenance_page.cards:
            if isinstance(card, MirrorCard):
                mirror_card = card
                break

        if mirror_card:
            selected_script = mirror_card.get_selected_mirror_script()
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
        if hasattr(self.maintenance_page, '_closing') and self.maintenance_page._closing:
            return
        if hasattr(self.fixes_page, '_closing') and self.fixes_page._closing:
            return

        actions_dir = get_actions_dir()
        scripts_dir = get_scripts_dir()

        final_path = os.path.join(actions_dir, '99_final.sh')
        if os.path.exists(final_path):
            os.remove(final_path)

        remaining = [f for f in os.listdir(actions_dir) if f.endswith('.sh')]

        if not remaining:
            self.reinitialize_program()
            return

        script_names = []
        for script in sorted(remaining):
            name = script.replace('_action.sh', '').replace('_rollback.sh', '')
            script_names.append(f"  • {name}")

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
        """Переинициализация программы без закрытия окна"""
        # Очищаем очередь действий
        clear_actions_dir()

        # Сбрасываем все чекбоксы на всех карточках
        for card in self.get_all_cards():
            if hasattr(card, 'install_cb'):
                card.install_cb.blockSignals(True)
                card.install_cb.setChecked(False)
                card.install_cb.blockSignals(False)
            if hasattr(card, 'rollback_cb'):
                card.rollback_cb.blockSignals(True)
                card.rollback_cb.setChecked(False)
                card.rollback_cb.blockSignals(False)

        # Запускаем скрипт проверки состояния системы
        self.run_check_state()

        # Обновляем стиль карточек в соответствии с флагами из state.d
        for card in self.get_all_cards():
            if hasattr(card, 'load_state'):
                card.load_state()

        # Сбрасываем радиокнопки выбора зеркала на "Не менять"
        mirror_card = self.get_mirror_card()
        if mirror_card and hasattr(mirror_card, 'none_radio'):
            mirror_card.none_radio.blockSignals(True)
            mirror_card.none_radio.setChecked(True)
            mirror_card.none_radio.blockSignals(False)
            if hasattr(mirror_card, 'load_state'):
                mirror_card.load_state()

        # Сбрасываем состояние рекомендованных кнопок
        self.recommended_state = False

    def show_help(self):
        if self.help_dialog is None:
            self.help_dialog = HelpDialog(self)
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def show_about(self):
        QMessageBox.about(
            self,
            "О программе Alt KDE Helper",
            f"<b>Alt KDE Helper</b><br><br>"
            f"Версия: {get_version()}<br><br>"
            "Программа для настройки и обслуживания<br>"
            "ALT Linux 11 с рабочим столом KDE6<br><br>"
            "Автор: kullibbin<br>"
            "<a href='mailto:kullibbin@gmail.com'>kullibbin@gmail.com</a><br><br>"
            "<a href='https://github.com/kullibbin-hub/alt-kde-helper'>GitHub</a>"
        )

    def check_for_updates(self):
        import urllib.request
        import json

        current_version = get_version()

        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/kullibbin-hub/alt-kde-helper/releases/latest",
                headers={"User-Agent": "Alt KDE Helper"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").lstrip("v")
                release_url = data.get("html_url", "")

            if latest_version and latest_version > current_version:
                msg = QMessageBox(self)
                msg.setWindowTitle("Доступно обновление")
                msg.setText(f"Доступна новая версия: {latest_version}\n\nВаша версия: {current_version}\n\nПерейти на страницу загрузки?")
                msg.setInformativeText("На странице GitHub вы сможете посмотреть изменения и скачать новый RPM.")
                msg.setStyleSheet("QLabel{min-width: 450px;}")
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg.setDefaultButton(QMessageBox.StandardButton.Yes)
                if msg.exec() == QMessageBox.StandardButton.Yes:
                    QDesktopServices.openUrl(QUrl(release_url))
            elif latest_version:
                QMessageBox.information(self, "Обновлений нет", f"У вас последняя версия {current_version}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось определить версию на GitHub")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось проверить обновления:\n{str(e)}")

    def edit_packages_list(self):
        import subprocess
        packages_file = get_packages_file_path()
        config_dir = get_config_dir()
        os.makedirs(config_dir, exist_ok=True)

        # Если файла нет — создаём из default
        if not os.path.exists(packages_file):
            default_file = get_default_packages_path()
            if os.path.exists(default_file):
                shutil.copy2(default_file, packages_file)
            else:
                open(packages_file, 'w').close()

        if subprocess.run(['which', 'kate'], capture_output=True).returncode == 0:
            editor = 'kate'
        elif subprocess.run(['which', 'kwrite'], capture_output=True).returncode == 0:
            editor = 'kwrite'
        else:
            editor = 'kwrite'

        subprocess.Popen([editor, packages_file])

    def reset_packages_list(self):
        config_dir = get_config_dir()
        current_version = get_current_version()
        current_file = get_packages_file_path()
        backup_file = os.path.join(config_dir, f'user_packages_{current_version}.old.txt')
        default_file = get_default_packages_path()

        # Создаём кастомный диалог с пояснениями и ссылкой
        dialog = QDialog(self)
        dialog.setWindowTitle("Восстановление списка пакетов")
        dialog.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Предупреждение
        warning = QLabel("<b>Восстановление списка пакетов по умолчанию</b>")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        layout.addSpacing(10)

        # Пояснение
        info = QLabel("Вы хотите заменить ваш текущий список пакетов на стандартный список по умолчанию (который идёт с программой).")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addSpacing(15)

        # Информация о бэкапе (кликабельная ссылка)
        backup_info = QLabel(
            f'📁 <b>Ваш текущий список не будет удалён.</b><br>'
            f'Он будет сохранён в той же папке как:<br>'
            f'<tt>user_packages_{current_version}.old.txt</tt><br><br>'
            f'Папка с настройками: <a href="file://{config_dir}">{config_dir}</a><br><br>'
            f'Если вы передумаете, вы сможете удалить новый список, а ваш старый<br>'
            f'переименовать обратно в <tt>user_packages_{current_version}.txt</tt> вручную.'
        )
        backup_info.setWordWrap(True)
        backup_info.setOpenExternalLinks(True)
        layout.addWidget(backup_info)

        layout.addSpacing(20)

        # Кнопки
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Восстановить")
        cancel_btn = QPushButton("Отмена")
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        def on_ok():
            dialog.done(1)

        def on_cancel():
            dialog.done(0)

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(on_cancel)

        result = dialog.exec()

        if result == 0:  # Отмена
            return

        # Выполняем восстановление
        # Если бэкап уже существует — удаляем его (держим только один последний)
        if os.path.exists(backup_file):
            os.remove(backup_file)

        # Переименовываем текущий файл в .old.txt
        if os.path.exists(current_file):
            os.rename(current_file, backup_file)

        # Копируем default → current
        if os.path.exists(default_file):
            shutil.copy2(default_file, current_file)
        else:
            open(current_file, 'w').close()

        QMessageBox.information(self, "Готово", "Список пакетов восстановлен.\n\nВаш старый список сохранён как .old.txt")

    def open_packages_folder(self):
        """Открывает папку с настройками программы в Dolphin"""
        config_dir = get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(config_dir))

    def create_fixes_page(self):
        cards = []

        # ============================================================
        # Без отката (SimpleActionCard)
        # ============================================================

        codec_card = SimpleActionCard(
            "Установка кодека openh264 для Flatpak (без VPN)",
            "Устанавливает кодек openh264 для Flatpak через stplr, для этого VPN не нужен.",
            "21_install_openh264_action.sh"
        )
        cards.append(codec_card)

        cards.append(SimpleActionCard(
            "Включить 3D-ускорение для Google Chrome (Flatpak)",
            "Включает аппаратное ускорение\nдля Google Chrome из Flatpak.",
            "16_flatpak_chrome_3d_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Разрешить загрузку тем и виджетов из сети",
            "Включает Get Hot New Stuff (ghns) в KDE",
            "17_enable_ghns_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Установка цветных значков papirus",
            "Будут установлены значки papirus-remix-icon-theme с разными цветами папок.\nУстановка может занимать несколько минут, из-за большого количества маленьких файлов,\nнаберитесь терпения.",
            "18_install_papirus_icons_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Добавить пользователя в группы (dialout, lp, adbusers)",
            "Добавляет текущего пользователя в группы \nдля доступа к USB-устройствам",
            "08_add_groups_action.sh"
        ))

        # ============================================================
        # С откатом (ActionCard)
        # ============================================================

        flatpak_card = ActionCard(
            "Установка Flatpak",
            "Устанавливает Flatpak, плагин для Discover,подключает репозиторий Flathub.\nВ случае удаления Flatpak будут удалены и все приложения из него.",
            "10_install_flatpak_action.sh",
            "10_install_flatpak_rollback.sh"
        )
        cards.append(flatpak_card)

        cards.append(ActionCard(
            "Установка или обновление eepm",
            "Устанавливает eepm, epmgpi, eepm-play-gui, \nобновляет eepm с сайта etersoft.",
            "06_install_eepm_action.sh",
            "06_install_eepm_rollback.sh"
        ))

        cards.append(ActionCard(
            "Установка stplr/aides",
            "Будут установлены stplr, плагин для Discover и репозиторий aides.\nВажно! В Discover пропадет возможность установки Google Chrome из Flatpak,\nвместо этого появится Google Chrome из Stapler! При необходимости можно удалить stplr по кнопке Откат,\nустановить Chrome из Flatpak, а потом установить stplr/aides.",
            "20_install_stplr_action.sh",
            "20_install_stplr_rollback.sh"
        ))

        home_access_card = ActionCard(
            "Доступ для flatpak ко всему домашнему каталогу на чтение",
            "Необходимо для перетаскивания файлов на окна flatpak-приложений.\n\nДетальная настройка прав:\nПараметры системы → Права доступа приложений →\n→ выбрать приложение → кнопка \"Управление параметрами flatpak\"",
            "11_flatpak_home_access_action.sh",
            "11_flatpak_home_access_rollback.sh"
        )
        cards.append(home_access_card)

        cards.append(ActionCard(
            "Размер шрифта 10",
            "Устанавливает базовый размер шрифта — 10",
            "13_increase_fonts_action.sh",
            "13_increase_fonts_rollback.sh"
        ))

        cards.append(ActionCard(
            "Исправить поведение индикатора копирования файлов",
            "Исправляет ситуацию, когда запись на флешку закончена\nпо индикатору копирования, а флешка еще долго не отмонтируется.",
            "12_fix_copy_indicator_action.sh",
            "12_fix_copy_indicator_rollback.sh"
        ))

        cards.append(ActionCard(
            "Показ миниатюр для 3D-файлов (STL, FCstd)",
            "Включается создание миниатюр для файлов .stl, .FCstd\nдля отображения в файлменеджере в режиме значков,\nдля программ 3D-моделирования FreeCAD, слайсеров и т. д.",
            "14_thumbnails_3d_action.sh",
            "14_thumbnails_3d_rollback.sh"
        ))

        cards.append(ActionCard(
            "Показ миниатюр для файлов .dwg (AutoCAD)",
            "Включается создание миниатюр для файлов .dwg (AutoCAD).\nБудет установлен NConvert, бесплатен для некоммерческого\nиспользования.",
            "15_thumbnails_dwg_action.sh",
            "15_thumbnails_dwg_rollback.sh"
        ))

        # Связываем: при включении flatpak включаем кодек и доступ к домашнему каталогу
        def on_flatpak_toggled(state):
            if state == Qt.CheckState.Checked.value:
                # Включаем кодек
                codec_card.install_cb.blockSignals(True)
                codec_card.install_cb.setChecked(True)
                codec_card.install_cb.blockSignals(False)
                codec_card.update_style('orange')

                # Включаем доступ к домашнему каталогу
                home_access_card.install_cb.blockSignals(True)
                home_access_card.install_cb.setChecked(True)
                home_access_card.install_cb.blockSignals(False)
                home_access_card.update_style('orange')

        flatpak_card.install_cb.stateChanged.connect(on_flatpak_toggled)

        cards.append(ActionCard(
            "Включить локальную сеть (samba)",
            "Включает в автозапуск сервисы smb и nmb для обеспечения\nработы локальной сети с протоколом SMB.\n\nПакеты samba и samba-client должны быть установлены.",
            "22_enable_samba_action.sh",
            "22_enable_samba_rollback.sh"
        ))

        return CategoryPage(cards)

    def create_maintenance_page(self):
        cards = []

        cards.append(MirrorCard())

        cards.append(SimpleActionCard(
            "Установка рекомендованных пакетов",
            f"Устанавливает пакеты из списка {get_packages_file_path()}\nСписок можно редактировать через меню в верхнем левом углу окна приложения",
            "07_install_packages_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Ремонт apt-get при ошибках",
            "apt-get dedup && pm --rebuilddb",
            "01_repair_apt_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Исправление ошибки с прокси в Discover",
            "Пересоздание кэша packagekit.\nУстраняет ошибку, когда Discover не подключается к сети\nпосле удаления локального прокси.",
            "09_fix_discover_proxy_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Обновление системы и программ из всех источников",
            "Будет обновлена система из репозитория (rpm-пакеты),\nа также обновятся и другие установленные в системе источники\nи программы из них.",
            "05_update_system_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Очистка кэша",
            "Очистка кэшей: в домашнем каталоге, для Flatpak-приложений,\nаккуратную очистку системного кэша, удаление старых журналов\nи сжатие до размера 100 МБ максимум, очистку кэша пакетов\n(без применения небезопасной опции autoremove),\nудаление неиспользуемых рантаймов Flatpak,\nудаление старых ядер.",
            "95_clean_cache_action.sh"
        ))

        return CategoryPage(cards)


def run():
    app = QApplication(sys.argv)
    # Применяем стили с учётом сохранённой настройки темы
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
