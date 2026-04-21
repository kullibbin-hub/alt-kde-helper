# gui.py - графический интерфейс Alt KDE Helper

import sys
import os
import shutil
import subprocess
import glob
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QFrame,
    QScrollArea, QMessageBox, QPushButton, QButtonGroup, QDialog, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon

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

    def run(self):
        scripts = sorted(glob.glob(os.path.join(self.actions_dir, '*.sh')))
        if not scripts:
            self.finished.emit()
            return

        cmd = 'for script in ' + ' '.join(f'"{s}"' for s in scripts) + '; do bash "$script"; done'
        process = subprocess.Popen(
            ['konsole', '--new-tab', '--title', 'Применение изменений', '-e', 'bash', '-c', cmd]
        )
        process.wait()
        self.finished.emit()


class ActionCard(QFrame):
    """Карточка с двумя чекбоксами для действия с откатом"""
    def __init__(self, description, tooltip_text, script_name, rollback_script_name, parent=None):
        super().__init__(parent)
        self.script_name = script_name
        self.rollback_script_name = rollback_script_name

        self.setProperty("class", "ActionCard")

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 4, 12, 4)

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
            self.desc_label.setProperty("class", "Description")
            self.setProperty("class", "ActionCard")
        self.style().unpolish(self)
        self.style().polish(self)
        self.desc_label.style().unpolish(self.desc_label)
        self.desc_label.style().polish(self.desc_label)

        self.rollback_cb.setEnabled(has_flag)
        self.install_cb.setChecked(False)
        self.rollback_cb.setChecked(False)

    def update_style(self, state_type):
        """state_type: 'normal', 'orange', 'green'"""
        if state_type == 'orange':
            self.desc_label.setProperty("class", "DescriptionOrange")
            self.setProperty("class", "ActionCardOrange")
        elif state_type == 'green':
            self.desc_label.setProperty("class", "DescriptionGreen")
            self.setProperty("class", "ActionCardGreen")
        else:  # normal
            self.desc_label.setProperty("class", "Description")
            self.setProperty("class", "ActionCard")
        self.style().unpolish(self)
        self.style().polish(self)
        self.desc_label.style().unpolish(self.desc_label)
        self.desc_label.style().polish(self.desc_label)

    def on_install_changed(self, state):
        actions_dir = get_actions_dir()
        action_path = os.path.join(actions_dir, self.script_name)
        rollback_path = os.path.join(actions_dir, self.rollback_script_name)

        is_checked = (state == Qt.CheckState.Checked.value)

        if is_checked:
            self.rollback_cb.blockSignals(True)
            self.rollback_cb.setChecked(False)
            self.rollback_cb.blockSignals(False)

            if os.path.exists(rollback_path):
                os.remove(rollback_path)

            script_src = os.path.join(get_scripts_dir(), self.script_name)
            if os.path.exists(script_src) and not os.path.exists(action_path):
                shutil.copy2(script_src, action_path)

            self.update_style('orange')
        else:
            if os.path.exists(action_path):
                os.remove(action_path)

            state_dir = get_state_dir()
            state_file = os.path.join(state_dir, self.script_name)
            if os.path.exists(state_file):
                self.update_style('green')
            else:
                self.update_style('normal')

    def on_rollback_changed(self, state):
        actions_dir = get_actions_dir()
        action_path = os.path.join(actions_dir, self.script_name)
        rollback_path = os.path.join(actions_dir, self.rollback_script_name)

        is_checked = (state == Qt.CheckState.Checked.value)

        if is_checked:
            self.install_cb.blockSignals(True)
            self.install_cb.setChecked(False)
            self.install_cb.blockSignals(False)

            if os.path.exists(action_path):
                os.remove(action_path)

            script_src = os.path.join(get_scripts_dir(), self.rollback_script_name)
            if os.path.exists(script_src) and not os.path.exists(rollback_path):
                shutil.copy2(script_src, rollback_path)

            self.update_style('orange')
        else:
            if os.path.exists(rollback_path):
                os.remove(rollback_path)

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
        layout.setContentsMargins(12, 4, 12, 4)

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
            self.desc_label.setProperty("class", "Description")
            self.setProperty("class", "SimpleActionCard")
        self.style().unpolish(self)
        self.style().polish(self)
        self.desc_label.style().unpolish(self.desc_label)
        self.desc_label.style().polish(self.desc_label)

        self.install_cb.setChecked(False)

    def update_style(self, state_type):
        """state_type: 'normal', 'orange', 'green'"""
        if state_type == 'orange':
            self.desc_label.setProperty("class", "DescriptionOrange")
            self.setProperty("class", "SimpleActionCardOrange")
        elif state_type == 'green':
            self.desc_label.setProperty("class", "DescriptionGreen")
            self.setProperty("class", "SimpleActionCardGreen")
        else:  # normal
            self.desc_label.setProperty("class", "Description")
            self.setProperty("class", "SimpleActionCard")
        self.style().unpolish(self)
        self.style().polish(self)
        self.desc_label.style().unpolish(self.desc_label)
        self.desc_label.style().polish(self.desc_label)

    def on_install_changed(self, state):
        actions_dir = get_actions_dir()
        action_path = os.path.join(actions_dir, self.script_name)

        is_checked = (state == Qt.CheckState.Checked.value)

        if is_checked:
            script_src = os.path.join(get_scripts_dir(), self.script_name)
            if os.path.exists(script_src) and not os.path.exists(action_path):
                shutil.copy2(script_src, action_path)
            self.update_style('orange')
        else:
            if os.path.exists(action_path):
                os.remove(action_path)

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
        frame_layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Выбор зеркала репозитория")
        title.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        frame_layout.addWidget(title)

        # Не менять
        self.none_script = "none"
        none_widget = QWidget()
        none_layout = QHBoxLayout()
        none_layout.setContentsMargins(0, 4, 0, 4)
        none_label = QLabel("Не менять текущее зеркало")
        none_label.setWordWrap(True)
        none_layout.addWidget(none_label, 1)
        none_radio = QPushButton()
        none_radio.setCheckable(True)
        none_radio.setProperty("class", "RadioButton")
        none_radio.setCursor(Qt.CursorShape.PointingHandCursor)
        none_radio.setFixedSize(20, 20)
        none_layout.addWidget(none_radio)
        none_widget.setLayout(none_layout)
        frame_layout.addWidget(none_widget)

        self.none_radio = none_radio
        self.none_label = none_label
        self.button_group.addButton(none_radio)

        # Три зеркала
        for script_name, description in self.mirrors:
            widget = QWidget()
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 4, 0, 4)

            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            h_layout.addWidget(desc_label, 1)

            radio = QPushButton()
            radio.setCheckable(True)
            radio.setProperty("class", "RadioButton")
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            radio.setFixedSize(20, 20)
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

        # Определяем, какое зеркало активно по флагу
        for script_name in self.radio_buttons.keys():
            state_file = os.path.join(state_dir, script_name)
            if os.path.exists(state_file):
                active_script = script_name
                break

        # Сбрасываем цвета
        for script_name, (radio, desc_label) in self.radio_buttons.items():
            desc_label.setProperty("class", "Description")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
        self.none_label.setProperty("class", "Description")
        self.none_label.style().unpolish(self.none_label)
        self.none_label.style().polish(self.none_label)

        # Устанавливаем радиокнопку "Не менять" (всегда)
        self.none_radio.setChecked(True)

        # Подсвечиваем активное зеркало зелёным
        if active_script:
            radio, desc_label = self.radio_buttons[active_script]
            desc_label.setProperty("class", "DescriptionGreen")
        else:
            self.none_label.setProperty("class", "DescriptionGreen")

        # Обновляем стили
        for script_name, (radio, desc_label) in self.radio_buttons.items():
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
        self.none_label.style().unpolish(self.none_label)
        self.none_label.style().polish(self.none_label)

        # Проверяем очередь - если какой-то скрипт зеркала в очереди, делаем его оранжевым
        actions_dir = get_actions_dir()
        for script_name, (radio, desc_label) in self.radio_buttons.items():
            action_path = os.path.join(actions_dir, script_name)
            if os.path.exists(action_path):
                desc_label.setProperty("class", "DescriptionOrange")
                desc_label.style().unpolish(desc_label)
                desc_label.style().polish(desc_label)

    def on_radio_toggled(self, radio, checked):
        if not checked:
            return

        actions_dir = get_actions_dir()
        mirror_scripts = list(self.radio_buttons.keys())

        # Находим выбранный скрипт
        selected_script = None
        for script_name, (r, desc_label) in self.radio_buttons.items():
            if r == radio:
                selected_script = script_name
                break

        # Удаляем из очереди все скрипты зеркал
        for script_name in mirror_scripts:
            action_path = os.path.join(actions_dir, script_name)
            if os.path.exists(action_path):
                os.remove(action_path)

        # Если выбрано конкретное зеркало - добавляем его в очередь
        if selected_script:
            script_src = os.path.join(get_scripts_dir(), selected_script)
            action_path = os.path.join(actions_dir, selected_script)
            if os.path.exists(script_src) and not os.path.exists(action_path):
                shutil.copy2(script_src, action_path)

            # Делаем выбранный пункт оранжевым
            _, desc_label = self.radio_buttons[selected_script]
            desc_label.setProperty("class", "DescriptionOrange")
            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)

            # Остальные делаем обычными (цвет определится при загрузке)
            for script_name, (r, lbl) in self.radio_buttons.items():
                if script_name != selected_script:
                    state_file = os.path.join(get_state_dir(), script_name)
                    if os.path.exists(state_file):
                        lbl.setProperty("class", "DescriptionGreen")
                    else:
                        lbl.setProperty("class", "Description")
                    lbl.style().unpolish(lbl)
                    lbl.style().polish(lbl)

            # none_label делаем обычным (если не было флага)
            state_dir = get_state_dir()
            any_flag = any(os.path.exists(os.path.join(state_dir, sn)) for sn in mirror_scripts)
            if not any_flag:
                self.none_label.setProperty("class", "Description")
            else:
                self.none_label.setProperty("class", "Description")
            self.none_label.style().unpolish(self.none_label)
            self.none_label.style().polish(self.none_label)

        else:
            # Выбрано "Не менять" - ничего не добавляем, все скрипты уже удалены
            # Возвращаем цвета в зависимости от флагов
            state_dir = get_state_dir()
            for script_name, (r, lbl) in self.radio_buttons.items():
                state_file = os.path.join(state_dir, script_name)
                if os.path.exists(state_file):
                    lbl.setProperty("class", "DescriptionGreen")
                else:
                    lbl.setProperty("class", "Description")
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)

            any_flag = any(os.path.exists(os.path.join(state_dir, sn)) for sn in mirror_scripts)
            if any_flag:
                self.none_label.setProperty("class", "Description")
            else:
                self.none_label.setProperty("class", "DescriptionGreen")
            self.none_label.style().unpolish(self.none_label)
            self.none_label.style().polish(self.none_label)

    def set_fast_mirror(self, enable):
        """Включает/выключает выбор самого быстрого зеркала"""
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


class HelpDialog(QDialog):
    """Немодальное окно справки (загружает HTML из файла)"""
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
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(10, 10, 10, 10)

        for card in cards:
            content_layout.addWidget(card)

        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.setLayout(layout)
        self.cards = cards

    def restart_program(self):
        """Перезапускает программу"""
        subprocess.Popen([sys.executable, sys.argv[0]])
        QApplication.quit()

    def apply(self):
        actions_dir = get_actions_dir()
        scripts_dir = get_scripts_dir()

        action_files = [f for f in os.listdir(actions_dir) if f.endswith('.sh') and f != '99_final.sh']
        if not action_files:
            QMessageBox.information(self, "Нет действий", "Нет действий для применения.")
            return

        final_script_src = os.path.join(scripts_dir, '99_final.sh')
        final_script_dst = os.path.join(actions_dir, '99_final.sh')
        if os.path.exists(final_script_src) and not os.path.exists(final_script_dst):
            shutil.copy2(final_script_src, final_script_dst)

        self.worker = ActionWorker(actions_dir)
        self.worker.finished.connect(self.on_actions_finished)
        self.worker.start()

    def on_actions_finished(self):
        actions_dir = get_actions_dir()
        scripts_dir = get_scripts_dir()

        final_path = os.path.join(actions_dir, '99_final.sh')
        if os.path.exists(final_path):
            os.remove(final_path)

        remaining = [f for f in os.listdir(actions_dir) if f.endswith('.sh')]

        if not remaining:
            self.restart_program()
            return

        # Есть остатки — спрашиваем
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Не все действия выполнены")
        msg_box.setText("Остались невыполненные действия.")
        msg_box.setInformativeText("Продолжить выполнение или отменить?")
        continue_btn = msg_box.addButton("Продолжить", QMessageBox.ButtonRole.YesRole)
        cancel_btn = msg_box.addButton("Отменить", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(continue_btn)
        msg_box.exec()

        if msg_box.clickedButton() == continue_btn:
            final_script_src = os.path.join(scripts_dir, '99_final.sh')
            final_script_dst = os.path.join(actions_dir, '99_final.sh')
            if os.path.exists(final_script_src) and not os.path.exists(final_script_dst):
                shutil.copy2(final_script_src, final_script_dst)
            self.worker = ActionWorker(actions_dir)
            self.worker.finished.connect(self.on_actions_finished)
            self.worker.start()
        else:
            self.restart_program()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alt KDE Helper")
        self.setObjectName("alt-kde-helper")
        self.setMinimumSize(870, 700)
        self.resize(870, 700)

        clear_actions_dir()

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Верхняя часть
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.tab_btn_fixes = QPushButton("Настройки")
        self.tab_btn_fixes.setProperty("class", "TabButtonActive")
        self.tab_btn_fixes.setCheckable(True)
        self.tab_btn_fixes.setChecked(True)
        self.tab_btn_fixes.clicked.connect(lambda: self.switch_tab(0))

        self.tab_btn_maintenance = QPushButton("Обслуживание")
        self.tab_btn_maintenance.setProperty("class", "TabButton")
        self.tab_btn_maintenance.setCheckable(True)
        self.tab_btn_maintenance.clicked.connect(lambda: self.switch_tab(1))

        tab_buttons_layout = QVBoxLayout()
        tab_buttons_layout.addWidget(self.tab_btn_fixes)
        tab_buttons_layout.addWidget(self.tab_btn_maintenance)
        tab_buttons_layout.addStretch()
        tab_buttons_widget = QWidget()
        tab_buttons_widget.setFixedWidth(180)
        tab_buttons_widget.setLayout(tab_buttons_layout)

        self.stack = QWidget()
        self.stack_layout = QVBoxLayout()
        self.stack_layout.setContentsMargins(0, 0, 0, 0)

        self.fixes_page = self.create_fixes_page()
        self.maintenance_page = self.create_maintenance_page()

        self.stack_layout.addWidget(self.fixes_page)
        self.stack_layout.addWidget(self.maintenance_page)
        self.maintenance_page.setVisible(False)

        self.stack.setLayout(self.stack_layout)

        top_layout.addWidget(tab_buttons_widget)
        top_layout.addWidget(self.stack, 1)
        main_layout.addLayout(top_layout)

        # Нижняя панель с кнопками
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 10, 10, 10)
        bottom_layout.setSpacing(10)

        self.recommended_btn = QPushButton("Выбрать рекомендованные настройки")
        self.recommended_btn.setProperty("class", "BottomButton")
        self.recommended_btn.clicked.connect(self.toggle_recommended)
        bottom_layout.addWidget(self.recommended_btn)

        bottom_layout.addStretch()

        self.apply_btn = QPushButton("Применить")
        self.apply_btn.setProperty("class", "BottomButton")
        self.apply_btn.setToolTip("После нажатия кнопки откроется терминал.\nВ нём будут выполняться указанные задания.\nДождитесь надписи об окончании, не закрывайте терминал раньше.")
        self.apply_btn.clicked.connect(self.apply_actions)
        bottom_layout.addWidget(self.apply_btn)

        bottom_layout.addStretch()

        self.help_btn = QPushButton("Помощь")
        self.help_btn.setProperty("class", "BottomButton")
        self.help_btn.clicked.connect(self.show_help)
        bottom_layout.addWidget(self.help_btn)

        main_layout.addLayout(bottom_layout)
        central.setLayout(main_layout)

        self.help_dialog = None
        self.recommended_state = False

        self.recommended_scripts = [
            "11_flatpak_home_access_action.sh",
            "12_fix_copy_indicator_action.sh",
            "13_increase_fonts_action.sh",
            "16_flatpak_chrome_3d_action.sh",
            "17_enable_ghns_action.sh",
            "08_add_groups_action.sh",
            "07_install_packages_action.sh",
            "02_repo_fast_mirror_action.sh",
            "05_update_system_action.sh",
            "06_update_eepm_action.sh",
            "95_clean_cache_action.sh"
        ]

    def switch_tab(self, index):
        self.fixes_page.setVisible(index == 0)
        self.maintenance_page.setVisible(index == 1)
        self.tab_btn_fixes.setChecked(index == 0)
        self.tab_btn_maintenance.setChecked(index == 1)

        self.tab_btn_fixes.setProperty("class", "TabButtonActive" if index == 0 else "TabButton")
        self.tab_btn_maintenance.setProperty("class", "TabButtonActive" if index == 1 else "TabButton")

        self.tab_btn_fixes.style().unpolish(self.tab_btn_fixes)
        self.tab_btn_fixes.style().polish(self.tab_btn_fixes)
        self.tab_btn_maintenance.style().unpolish(self.tab_btn_maintenance)
        self.tab_btn_maintenance.style().polish(self.tab_btn_maintenance)

    def get_all_cards(self):
        cards = []
        if hasattr(self.fixes_page, 'cards'):
            cards.extend(self.fixes_page.cards)
        if hasattr(self.maintenance_page, 'cards'):
            cards.extend(self.maintenance_page.cards)
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
            # Включаем все рекомендованные чекбоксы
            for card in cards:
                if hasattr(card, 'install_cb') and hasattr(card, 'script_name'):
                    if card.script_name in self.recommended_scripts:
                        card.install_cb.setChecked(True)
            if mirror_card:
                mirror_card.set_fast_mirror(True)
            self.recommended_state = True
        else:
            # Выключаем все рекомендованные чекбоксы
            for card in cards:
                if hasattr(card, 'install_cb') and hasattr(card, 'script_name'):
                    if card.script_name in self.recommended_scripts:
                        card.install_cb.setChecked(False)
            if mirror_card:
                mirror_card.set_fast_mirror(False)
            self.recommended_state = False

    def apply_actions(self):
        current_page = self.fixes_page if self.fixes_page.isVisible() else self.maintenance_page
        current_page.apply()

    def show_help(self):
        if self.help_dialog is None:
            self.help_dialog = HelpDialog(self)
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def create_fixes_page(self):
        cards = []

        cards.append(ActionCard(
            "Доступ для flatpak ко всему домашнему каталогу на чтение",
            "Необходимо для перетаскивания файлов на окна flatpak-приложений.\n\nДетальная настройка прав:\nПараметры системы → Права доступа приложений →\n→ выбрать приложение → кнопка \"Управление параметрами flatpak\"",
            "11_flatpak_home_access_action.sh",
            "11_flatpak_home_access_rollback.sh"
        ))

        cards.append(ActionCard(
            "Исправить поведение индикатора копирования файлов",
            "Исправляет ситуацию, когда запись на флешку закончена\nпо индикатору копирования, а флешка еще долго не отмонтируется.",
            "12_fix_copy_indicator_action.sh",
            "12_fix_copy_indicator_rollback.sh"
        ))

        cards.append(ActionCard(
            "Размер шрифта 10",
            "Устанавливает базовый размер шрифта — 10",
            "13_increase_fonts_action.sh",
            "13_increase_fonts_rollback.sh"
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
            "Установка Flatpak и репозитория Flathub",
            "Устанавливает Flatpak, плагин для Discover,\nподключает репозиторий Flathub.",
            "19_install_flatpak_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Установка stplr / aides",
            "Будут установлены stplr и репозиторий aides.",
            "20_install_stplr_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Добавить пользователя в группы (dialout, lp, adbusers)",
            "Добавляет текущего пользователя в группы \nдля доступа к USB-устройствам",
            "08_add_groups_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Установка рекомендованных пакетов",
            "sudo synaptic-usermode epmgpi eepm-play-gui gearlever android-tools pipewire-jack git skanlite print-manager sane-airscan airsane gnome-disk-utility icon-theme-Papirus xdg-desktop-portal-gtk net-snmp kcm-grub2 kaccounts-providers avahi-daemon avahi-tools ffmpegthumbnailer mediainfo samba-usershares kdeconnect kamoso kio-admin stmpclean",
            "07_install_packages_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Установка кодека openh264 для Flatpak (без VPN)",
            "Устанавливает кодек openh264 для Flatpak через stplr, для этого VPN не нужен.",
            "21_install_openh264_action.sh"
        ))

        return CategoryPage(cards)

    def create_maintenance_page(self):
        cards = []

        cards.append(MirrorCard())

        cards.append(SimpleActionCard(
            "Ремонт apt-get при ошибках",
            "apt-get dedup && pm --rebuilddb",
            "01_repair_apt_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Обновление системы",
            "Обновление системы из репозитория и Flatpak",
            "05_update_system_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Установить / обновить eepm",
            "sudo epm upgrade https://download.etersoft.ru/pub/Korinf/x86_64/ALTLinux/p11/eepm-*.noarch.rpm\nЕсли он не установлен, то сначала устанавливает из репозитория.",
            "06_update_eepm_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Исправление ошибки с прокси в Discover",
            "Пересоздание кэша packagekit.\nУстраняет ошибку, когда Discover не подключается к сети\nпосле удаления локального прокси.",
            "09_fix_discover_proxy_action.sh"
        ))

        cards.append(SimpleActionCard(
            "Очистка кэша",
            "Очистка кэшей: в домашнем каталоге, для Flatpak-приложений,\nаккуратную очистку системного кэша, удаление старых журналов\nи сжатие до размера 100 МБ максимум, очистку кэша пакетов\n(без применения небезопасной опции autoremove),\nудаление неиспользуемых рантаймов Flatpak,\nудаление старых ядер.",
            "95_clean_cache_action.sh"
        ))

        return CategoryPage(cards)
