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
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QPoint
from PyQt6.QtGui import QDesktopServices, QIcon, QCloseEvent, QAction

from config import (
    STYLESHEET, get_scripts_dir, get_state_dir, get_actions_dir,
    clear_actions_dir, get_help_path
)


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
            ("03_repo_yandex_action.sh", "Сменить зеркало на Yandex"),
            ("04_repo_p11_action.sh", "Репозиторий по умолчанию (p11)"),
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
        self.setMinimumSize(870, 650)
        self.resize(870, 650)

        clear_actions_dir()

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Верхняя часть с категориями и меню
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        # Левая панель с кнопками категорий и меню
        left_panel = QWidget()
        left_panel.setFixedWidth(180)
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(5)

        # Кнопка-меню с системной иконкой KDE
        self.menu_button = QPushButton()
        self.menu_button.setIcon(QIcon.fromTheme("view-more-symbolic"))
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

        # Отступ сверху перед кнопками категорий (20 пикселей)
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

        top_layout.addWidget(left_panel)
        top_layout.addWidget(self.stack, 1)
        main_layout.addLayout(top_layout)

        # Нижняя панель с кнопками
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 10, 10, 10)
        bottom_layout.setSpacing(10)

        bottom_layout.addStretch()

        self.recommended_btn = QPushButton("Выбрать рекомендованные настройки")
        self.recommended_btn.setProperty("class", "BottomButton")
        self.recommended_btn.clicked.connect(self.toggle_recommended)
        bottom_layout.addWidget(self.recommended_btn)

        bottom_layout.addSpacing(10)

        self.apply_btn = QPushButton("Применить")
        self.apply_btn.setProperty("class", "BottomButton")
        self.apply_btn.setToolTip("После нажатия кнопки откроется терминал.\nВ нём будут выполняться указанные задания.\nДождитесь надписи об окончании, не закрывайте терминал раньше.")
        self.apply_btn.clicked.connect(self.apply_actions)
        bottom_layout.addWidget(self.apply_btn)

        main_layout.addLayout(bottom_layout)
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

        # Обновляем состояние карточек после проверки
        for card in self.get_all_cards():
            if hasattr(card, 'load_state'):
                card.load_state()

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

        menu.exec(self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height())))

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
        mirror_card = self.get_mirror_card()

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
            "Будут установлены значки papirus с разными цветами папок.\nУстановка может занимать несколько минут,\nиз-за большого количества маленьких файлов, наберитесь терпения.",
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

        return CategoryPage(cards)

    def create_maintenance_page(self):
        cards = []

        cards.append(MirrorCard())

        cards.append(SimpleActionCard(
            "Установка/переустановка рекомендованных пакетов",
            "Устанавливает или переустанавливает:\nsudo synaptic-usermode epmgpi eepm-play-gui gearlever android-tools pipewire-jack git skanlite print-manager sane-airscan airsane gnome-disk-utility icon-theme-Papirus xdg-desktop-portal-gtk net-snmp kcm-grub2 kaccounts-providers avahi-daemon avahi-tools ffmpegthumbnailer mediainfo samba-usershares kdeconnect kamoso kio-admin",
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
