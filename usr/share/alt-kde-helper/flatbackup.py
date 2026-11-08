# flatbackup.py - страница создания бэкапа Flatpak

import os
import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QButtonGroup,
    QPushButton, QTreeWidget, QTreeWidgetItem, QFileDialog, QInputDialog,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

from flatcommon import (
    run_in_konsole, parse_desktop_name, get_installed_apps,
    get_running_apps, du_sb, df_free, human_size, format_sizes,
    C_CYAN, C_YELLOW, C_GREEN, C_RED, C_RESET,
)
from busy import BUSY

# Цвет для сообщений о загрузке (красный)
LOADING_STYLE = "color: #d32f2f;"


class DataLoader(QThread):
    """Асинхронно собирает список приложений и их размеры.
    apps_ready: (all_apps, names, has_data)
    sizes_ready: (raw_system, raw_user, raw_data)"""
    apps_ready = pyqtSignal(list, dict, dict)
    sizes_ready = pyqtSignal(object, object, object)
    error = pyqtSignal(str)

    def run(self):
        try:
            all_apps = list(get_installed_apps())
            names = {a: parse_desktop_name(a) for a in all_apps}
            all_apps.sort(key=lambda a: names[a].lower())
            has_data = {
                a: os.path.isdir(os.path.expanduser(f'~/.var/app/{a}'))
                for a in all_apps
            }
            self.apps_ready.emit(all_apps, names, has_data)

            raw_system = du_sb('/var/lib/flatpak')
            raw_user = du_sb(os.path.expanduser('~/.local/share/flatpak'))
            raw_data = {}
            for a in all_apps:
                if has_data[a]:
                    raw_data[a] = du_sb(os.path.expanduser(f'~/.var/app/{a}'))
            self.sizes_ready.emit(raw_system, raw_user, raw_data)
        except Exception as e:
            self.error.emit(str(e))


class FlatpakBackupPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.worker = None
        self._loader = None
        self._loader_started = False
        self._temp_dir = None
        self._target_dir = None
        self._loading = True

        self._all_apps = []
        self._app_names = {}
        self._app_has_data = {}
        self._raw_system = 0
        self._raw_user = 0
        self._raw_data = {}

        layout = QVBoxLayout()

        mode_title = QLabel("Режим:")
        mode_title.setStyleSheet("font-weight: bold;")
        layout.addWidget(mode_title)

        mode_layout = QVBoxLayout()
        self.radio_full = QRadioButton("Полный бэкап (программы + данные, все приложения)")
        self.radio_data = QRadioButton("Только данные приложений")
        self.radio_list = QRadioButton("Создать список для быстрой установки онлайн")
        self.radio_full.setChecked(True)
        self.mode_group = QButtonGroup(self)
        for r in (self.radio_full, self.radio_data, self.radio_list):
            self.mode_group.addButton(r)
            mode_layout.addWidget(r)
        layout.addLayout(mode_layout)
        layout.addSpacing(10)

        self.tree_backup = QTreeWidget()
        self.tree_backup.setHeaderLabels(["Приложение", "Данные"])
        self.tree_backup.setColumnWidth(0, 640)
        self.tree_backup.setColumnWidth(1, 100)
        self.tree_backup.setRootIsDecorated(False)
        self.tree_backup.setAlternatingRowColors(True)
        self.tree_backup.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tree_backup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.tree_backup, 1)

        self.tree_list = QTreeWidget()
        self.tree_list.setHeaderLabels(["Приложение", "Выбор"])
        self.tree_list.setColumnWidth(0, 640)
        self.tree_list.setColumnWidth(1, 100)
        self.tree_list.setRootIsDecorated(False)
        self.tree_list.setAlternatingRowColors(True)
        self.tree_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tree_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree_list.setVisible(False)
        layout.addWidget(self.tree_list, 1)

        self.size_label = QLabel("Загрузка списка приложений... (пожалуйста, подождите)")
        self.size_label.setWordWrap(True)
        self.size_label.setStyleSheet(LOADING_STYLE)
        layout.addWidget(self.size_label)

        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_none = QPushButton("Снять выбор")
        self.btn_apply = QPushButton("Создать")
        self.btn_apply.setIcon(QIcon.fromTheme("document-save"))
        self.btn_create = QPushButton("Создать")
        self.btn_create.setIcon(QIcon.fromTheme("document-save"))
        for b in (self.btn_select_all, self.btn_select_none,
                  self.btn_apply, self.btn_create):
            b.setProperty("class", "BottomButton")

        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_select_none)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_create)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.radio_full.toggled.connect(self._on_mode_changed)
        self.radio_data.toggled.connect(self._on_mode_changed)
        self.radio_list.toggled.connect(self._on_mode_changed)
        self.tree_backup.itemChanged.connect(self._on_tree_backup_changed)
        self.btn_select_all.clicked.connect(self._on_select_all)
        self.btn_select_none.clicked.connect(self._on_select_none)
        self.btn_apply.clicked.connect(self._on_apply_list)
        self.btn_create.clicked.connect(self._on_create)

        BUSY.changed.connect(self._on_busy_changed)

        self._lock_ui(True)

    # --- ленивая загрузка при первом показе ---

    def showEvent(self, event):
        super().showEvent(event)
        if not self._loader_started:
            self._loader_started = True
            self._start_loader()

    def _start_loader(self):
        self._loader = DataLoader(self)
        self._loader.apps_ready.connect(self._on_apps_ready)
        self._loader.sizes_ready.connect(self._on_sizes_ready)
        self._loader.error.connect(self._on_loader_error)
        self._loader.start()

    # --- асинхронная загрузка ---

    def _on_apps_ready(self, all_apps, names, has_data):
        self._all_apps = all_apps
        self._app_names = names
        self._app_has_data = has_data
        self._fill_backup_tree()
        self._fill_list_tree()
        self.size_label.setStyleSheet(LOADING_STYLE)
        self.size_label.setText("Подсчёт размеров...")

    def _on_sizes_ready(self, raw_system, raw_user, raw_data):
        self._raw_system = raw_system
        self._raw_user = raw_user
        self._raw_data = raw_data
        self._loading = False
        self._lock_ui(False)
        self._update_create_enabled()
        self._on_mode_changed()

    def _on_loader_error(self, msg):
        self._loading = False
        self._lock_ui(False)
        self.btn_apply.setEnabled(False)
        self.btn_create.setEnabled(False)
        self.size_label.setStyleSheet(LOADING_STYLE)
        self.size_label.setText("Загрузка не удалась.")
        QMessageBox.critical(self, "Ошибка",
                             f"Не удалось получить список приложений:\n{msg}")

    def _on_busy_changed(self, busy):
        self._update_create_enabled()

    def _update_create_enabled(self):
        # btn_create доступна, только если данные загружены и konsole не работает
        can = (not self._loading) and (not BUSY.is_busy())
        self.btn_create.setEnabled(can)
        # btn_apply (для режима «список») — тоже
        if not self._loading:
            self.btn_apply.setEnabled(True)

    # --- заполнение деревьев ---

    def _fill_backup_tree(self):
        self.tree_backup.blockSignals(True)
        self.tree_backup.clear()
        for app_id in self._all_apps:
            name = self._app_names[app_id]
            display = f"{name} ({app_id})" if name != app_id else app_id
            item = QTreeWidgetItem([display, ''])
            item.setData(0, Qt.ItemDataRole.UserRole, app_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(1, Qt.CheckState.Unchecked)
            self.tree_backup.addTopLevelItem(item)
        self.tree_backup.blockSignals(False)

    def _fill_list_tree(self):
        self.tree_list.blockSignals(True)
        self.tree_list.clear()
        for app_id in self._all_apps:
            name = self._app_names[app_id]
            display = f"{name} ({app_id})" if name != app_id else app_id
            item = QTreeWidgetItem([display, ''])
            item.setData(0, Qt.ItemDataRole.UserRole, app_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(1, Qt.CheckState.Checked)
            self.tree_list.addTopLevelItem(item)
        self.tree_list.blockSignals(False)

    # --- режим ---

    def _on_mode_changed(self):
        if self._loading:
            return
        is_list = self.radio_list.isChecked()
        if is_list:
            self.tree_backup.setVisible(False)
            self.tree_list.setVisible(True)
            self.btn_select_all.setVisible(True)
            self.btn_select_none.setVisible(True)
            self.btn_apply.setVisible(True)
            self.btn_create.setVisible(False)
            self.size_label.setVisible(False)
            return

        self.tree_backup.setVisible(True)
        self.tree_list.setVisible(False)
        self.btn_apply.setVisible(False)
        self.btn_create.setVisible(True)
        self.size_label.setVisible(True)

        is_full = self.radio_full.isChecked()

        # «Выбрать все / Снять выбор» — только в режиме «Только данные»
        self.btn_select_all.setVisible(not is_full)
        self.btn_select_none.setVisible(not is_full)

        # В полном бэкапе колонка «Данные» скрыта целиком:
        # чекбоксы disabled и не должны провоцировать клики
        self.tree_backup.setColumnHidden(1, is_full)

        self.tree_backup.blockSignals(True)
        for i in range(self.tree_backup.topLevelItemCount()):
            item = self.tree_backup.topLevelItem(i)
            app_id = item.data(0, Qt.ItemDataRole.UserRole)
            has_data = self._app_has_data.get(app_id, False)
            if is_full:
                item.setHidden(False)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            else:
                if has_data:
                    item.setHidden(False)
                    item.setCheckState(1, Qt.CheckState.Checked)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                else:
                    item.setHidden(True)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        self.tree_backup.blockSignals(False)
        self._update_size_label()

    def _update_size_label(self):
        if self._loading:
            return
        self.size_label.setStyleSheet("")
        if self.radio_full.isChecked():
            est_prog = (self._raw_system + self._raw_user) * 0.4
            est_data = sum(self._raw_data.values()) * 0.5
            est = est_prog + est_data
            total_s, prog_s, data_s = format_sizes(est, est_prog, est_data)
            self.size_label.setText(
                f"Оценка размера бэкапа: ~{total_s} "
                f"(программы ~{prog_s}, данные ~{data_s})"
            )
        elif self.radio_data.isChecked():
            selected_sum = 0
            for i in range(self.tree_backup.topLevelItemCount()):
                item = self.tree_backup.topLevelItem(i)
                if item.checkState(1) == Qt.CheckState.Checked:
                    app_id = item.data(0, Qt.ItemDataRole.UserRole)
                    selected_sum += self._raw_data.get(app_id, 0)
            est = selected_sum * 0.5
            self.size_label.setText(
                f"Оценка размера бэкапа данных: ~{human_size(est)}"
            )

    def _on_tree_backup_changed(self, item, column):
        if column == 1 and self.radio_data.isChecked():
            self._update_size_label()

    # --- выбор ---

    def _on_select_all(self):
        if self.radio_data.isChecked():
            self.tree_backup.blockSignals(True)
            for i in range(self.tree_backup.topLevelItemCount()):
                item = self.tree_backup.topLevelItem(i)
                if item.isHidden():
                    continue
                if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    item.setCheckState(1, Qt.CheckState.Checked)
            self.tree_backup.blockSignals(False)
            self._update_size_label()
            return
        self.tree_list.blockSignals(True)
        for i in range(self.tree_list.topLevelItemCount()):
            item = self.tree_list.topLevelItem(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(1, Qt.CheckState.Checked)
        self.tree_list.blockSignals(False)

    def _on_select_none(self):
        if self.radio_data.isChecked():
            self.tree_backup.blockSignals(True)
            for i in range(self.tree_backup.topLevelItemCount()):
                item = self.tree_backup.topLevelItem(i)
                if item.isHidden():
                    continue
                if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    item.setCheckState(1, Qt.CheckState.Unchecked)
            self.tree_backup.blockSignals(False)
            self._update_size_label()
            return
        self.tree_list.blockSignals(True)
        for i in range(self.tree_list.topLevelItemCount()):
            item = self.tree_list.topLevelItem(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(1, Qt.CheckState.Unchecked)
        self.tree_list.blockSignals(False)

    # --- список для онлайн-установки ---

    def _on_apply_list(self):
        if BUSY.is_busy():
            return
        selected = []
        for i in range(self.tree_list.topLevelItemCount()):
            item = self.tree_list.topLevelItem(i)
            if item.checkState(1) == Qt.CheckState.Checked:
                selected.append(item.data(0, Qt.ItemDataRole.UserRole))
        if not selected:
            QMessageBox.warning(self, "Ничего не выбрано",
                                "Выберите хотя бы одно приложение.")
            return
        selected.sort(key=lambda a: self._app_names[a].lower())

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить скрипт установки",
            os.path.expanduser('~/flatpak-install.sh'),
            "Скрипт (*.sh)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return
        if not path.endswith('.sh'):
            path += '.sh'

        lines = ['#!/bin/sh', '']
        for app_id in selected:
            name = self._app_names[app_id]
            lines.append(f'flatpak install -y flathub {app_id} #{name}')

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
            os.chmod(path, 0o755)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Не удалось сохранить скрипт:\n{e}")
            return
        QMessageBox.information(self, "Готово", f"Скрипт сохранён:\n{path}")

    # --- создание бэкапа ---

    def _on_create(self):
        if self._loading or BUSY.is_busy():
            return

        parent_dir = QFileDialog.getExistingDirectory(
            self, "Выберите папку для бэкапа", os.path.expanduser('~/'),
            options=QFileDialog.Option.ShowDirsOnly,
        )
        if not parent_dir:
            return

        name, ok = QInputDialog.getText(
            self, "Имя бэкапа",
            "Введите имя папки бэкапа (без расширения .backup):"
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        if '/' in name or '\\' in name or name in ('.', '..'):
            QMessageBox.critical(self, "Ошибка", "Недопустимое имя папки.")
            return

        target = os.path.join(parent_dir, name + '.backup')

        overwrite = False
        if os.path.exists(target):
            ret = QMessageBox.question(
                self, "Папка уже существует",
                f"Папка {name}.backup уже существует. Перезаписать?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return
            overwrite = True

        backup_type = 'full' if self.radio_full.isChecked() else 'data_only'

        if backup_type == 'full':
            apps_to_backup = list(self._all_apps)
            apps_with_data = [a for a in self._all_apps if self._app_has_data[a]]
        else:
            selected = []
            for i in range(self.tree_backup.topLevelItemCount()):
                item = self.tree_backup.topLevelItem(i)
                if item.checkState(1) == Qt.CheckState.Checked:
                    app_id = item.data(0, Qt.ItemDataRole.UserRole)
                    if self._app_has_data.get(app_id):
                        selected.append(app_id)
            apps_with_data = selected
            apps_to_backup = list(selected)

        if not apps_with_data:
            QMessageBox.warning(
                self, "Нет данных",
                "Нет приложений с данными для бэкапа."
            )
            return

        raw_system = self._raw_system if backup_type == 'full' else 0
        raw_user = self._raw_user if backup_type == 'full' else 0
        raw_data_sum = sum(self._raw_data.get(a, 0) for a in apps_with_data)
        estimate = (raw_system + raw_user) * 0.4 + raw_data_sum * 0.5
        need = int(estimate * 1.5)
        free = df_free(parent_dir)
        if need > free:
            need_s, free_s = format_sizes(need, free)
            QMessageBox.critical(
                self, "Недостаточно места",
                f"Недостаточно свободного места на разделе назначения.\n\n"
                f"Требуется: ~{need_s}\n"
                f"Свободно: {free_s}\n\n"
                f"Освободите место или выберите другой раздел."
            )
            return

        running = get_running_apps()

        prep_msg = (
            "Перед созданием бэкапа будут закрыты все запущенные Flatpak-приложения\n"
            "(иначе их настройки и данные могут сохраниться в повреждённом виде),\n"
            "будут очищены кэши Flatpak-приложений и удалены неиспользуемые рантаймы Flatpak.\n\n"
        )
        if running:
            names = ', '.join(sorted(running))
            prep_msg += f"Сейчас запущены: {names}\n\n"
        prep_msg += "При отказе бэкап создан не будет.\n\nПродолжить?"

        ret = QMessageBox.question(
            self, "Подготовка к бэкапу",
            prep_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        if running:
            for app_id in running:
                subprocess.run(['flatpak', 'kill', app_id], check=False)
            time.sleep(1)
            still = get_running_apps()
            if still:
                names2 = '\n'.join(f'  • {a}' for a in still)
                QMessageBox.critical(
                    self, "Не удалось закрыть приложения",
                    f"Не удалось закрыть приложения:\n{names2}\n\n"
                    f"Закройте их вручную и попробуйте снова."
                )
                return

        if overwrite and os.path.exists(target):
            try:
                shutil.rmtree(target, ignore_errors=True)
            except Exception:
                pass

        has_system_repo = os.path.isdir('/var/lib/flatpak')
        has_user_repo = os.path.isdir(os.path.expanduser('~/.local/share/flatpak'))

        try:
            temp_dir = tempfile.mkdtemp(prefix='alt-flatbackup-')
            self._temp_dir = temp_dir
            self._target_dir = target

            meta = {
                'created': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'backup_type': backup_type,
                'user': os.environ.get('USER', ''),
            }
            if backup_type == 'full':
                meta['has_system_repo'] = has_system_repo
                meta['has_user_repo'] = has_user_repo

            meta_apps = []
            for app_id in apps_to_backup:
                meta_apps.append({
                    'id': app_id,
                    'name': self._app_names[app_id],
                    'has_data': self._app_has_data[app_id],
                })
            meta['apps'] = meta_apps

            with open(os.path.join(temp_dir, 'meta.json'), 'w',
                      encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            script = self._build_bash_script(
                target, temp_dir, backup_type,
                has_system_repo, has_user_repo,
                apps_to_backup, apps_with_data,
            )
            script_path = os.path.join(temp_dir, 'backup.sh')
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script)
            os.chmod(script_path, 0o755)
        except Exception as e:
            self._cleanup_temp()
            QMessageBox.critical(self, "Ошибка",
                                 f"Не удалось подготовить бэкап:\n{e}")
            return

        self._lock_ui(True)
        self.worker = run_in_konsole(
            script_path, f"Бэкап Flatpak: {name}",
            self._on_worker_finished, parent=self,
        )

    def _build_bash_script(self, target, temp_dir, backup_type,
                           has_system_repo, has_user_repo,
                           apps_to_backup, apps_with_data):
        t = target
        sizes = os.path.join(temp_dir, 'sizes.txt')
        meta = os.path.join(temp_dir, 'meta.json')
        manifest = os.path.join(target, 'manifest.json')
        base_name = os.path.basename(target)

        expected_archives = []
        if backup_type == 'full' and has_system_repo:
            expected_archives.append('flatpak-system.tar.zst')
        if backup_type == 'full' and has_user_repo:
            expected_archives.append('flatpak-user.tar.zst')
        if apps_with_data:
            expected_archives.append('data.tar.zst')

        L = []
        L.append('#!/bin/bash')
        L.append('')
        L.append(f'echo -e "{C_CYAN}========================================{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}Создание бэкапа Flatpak: {base_name}{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}========================================{C_RESET}"')
        L.append('')



        L.append(f'printf "\\r\\033[K"; echo -e "{C_YELLOW}→ Подсчёт размеров...{C_RESET}"')
        L.append(f'SIZES="{sizes}"')
        L.append(': > "$SIZES"')
        if backup_type == 'full':
            if has_system_repo:
                L.append('echo "system=$(du -sb /var/lib/flatpak | cut -f1)" >> "$SIZES"')
            if has_user_repo:
                L.append('echo "user=$(du -sb ~/.local/share/flatpak | cut -f1)" >> "$SIZES"')
        for app_id in apps_with_data:
            L.append(
                f'if [ -d ~/.var/app/{app_id} ]; then '
                f'echo "{app_id}=$(du -sb ~/.var/app/{app_id} | cut -f1)" >> "$SIZES"; '
                f'fi'
            )
        L.append('')

        L.append('(')
        L.append('    while true; do')
        L.append(f'        if [ -d "{t}" ]; then')
        L.append(f'            _sz=$(du -sh "{t}" 2>/dev/null | cut -f1 | sed -E \'s/([0-9])([A-Za-z]+)$/\\1 \\2/\')')
        L.append('            if [ -n "$_sz" ]; then')
        L.append('                printf "\\r\\033[K\\033[1;36m   Размер бэкапа: %s   \\033[0m" "$_sz"')
        L.append('            fi')
        L.append('        fi')
        L.append('        sleep 5')
        L.append('    done')
        L.append(') &')
        L.append('MONITOR=$!')
        L.append('')

        if backup_type == 'full' and has_system_repo:
            L.append(f'printf "\\r\\033[K"; echo -e "{C_YELLOW}→ Архивирование системного репозитория...{C_RESET}"')
            L.append(f'tar -I \'zstd -3 -T0\' --xattrs --xattrs-include=\'*\' -cf "{t}/flatpak-system.tar.zst" '
                     f'--exclude=\'*.lock\' -C / var/lib/flatpak')
            L.append('')
        if backup_type == 'full' and has_user_repo:
            L.append(f'printf "\\r\\033[K"; echo -e "{C_YELLOW}→ Архивирование пользовательского репозитория...{C_RESET}"')
            L.append(f'tar -I \'zstd -3 -T0\' --xattrs --xattrs-include=\'*\' -cf "{t}/flatpak-user.tar.zst" '
                     f'--exclude=\'*.lock\' -C ~/.local/share flatpak')
            L.append('')

        if apps_with_data:
            L.append(f'printf "\\r\\033[K"; echo -e "{C_YELLOW}→ Архивирование данных приложений ({len(apps_with_data)})...{C_RESET}"')
            dirs = ' '.join(apps_with_data)
            L.append(f'tar -I \'zstd -3 -T0\' --xattrs --xattrs-include=\'*\' -cf "{t}/data.tar.zst" -C ~/.var/app {dirs}')
            L.append('')

        L.append('kill $MONITOR 2>/dev/null')
        L.append('wait $MONITOR 2>/dev/null')
        L.append('printf "\\r\\033[K"')
        L.append('')
        L.append(f'echo -e "{C_YELLOW}→ Проверка целостности созданных архивов...{C_RESET}"')
        L.append('CHECK_FAILED=0')
        for arc in expected_archives:
            L.append(f'if [ ! -f "{t}/{arc}" ]; then')
            L.append(f'    echo -e "{C_RED}  {arc} — файл не создан{C_RESET}"')
            L.append('    CHECK_FAILED=1')
            L.append('else')
            L.append(f'    echo -n "  {arc} ... "')
            L.append(f'    if tar -I \'zstd -d -T0\' -tf "{t}/{arc}" >/dev/null 2>&1; then')
            L.append('        echo "ok"')
            L.append('    else')
            L.append(f'        echo -e "{C_RED}повреждён{C_RESET}"')
            L.append('        CHECK_FAILED=1')
            L.append('    fi')
            L.append('fi')
        L.append('if [ "$CHECK_FAILED" -ne 0 ]; then')
        L.append(f'    echo ""')
        L.append(f'    echo -e "{C_RED}❌ Архивация не завершена. Один или несколько архивов повреждены.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Наиболее вероятная причина — нехватка свободного места на диске.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Манифест не создан, бэкап не может быть использован для восстановления.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Папка бэкапа будет удалена программой после закрытия этого окна.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Нажмите любую клавишу для выхода...{C_RESET}"')
        L.append('    read -n1')
        L.append('    exit 1')
        L.append('fi')
        L.append('')

        L.append(f'echo -e "{C_YELLOW}→ Создание манифеста...{C_RESET}"')
        L.append(f'python3 - "{meta}" "$SIZES" "{manifest}" <<\'PYEOF\'')
        L.append('import json, sys')
        L.append('meta_path, sizes_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]')
        L.append('with open(meta_path) as f:')
        L.append('    meta = json.load(f)')
        L.append('sizes = {}')
        L.append('with open(sizes_path) as f:')
        L.append('    for line in f:')
        L.append('        line = line.strip()')
        L.append('        if "=" in line:')
        L.append('            k, v = line.split("=", 1)')
        L.append('            try:')
        L.append('                sizes[k] = int(v)')
        L.append('            except ValueError:')
        L.append('                sizes[k] = 0')
        L.append('BUF = 1.05')
        L.append('out = {}')
        L.append('out["created"] = meta["created"]')
        L.append('out["backup_type"] = meta["backup_type"]')
        L.append('out["user"] = meta["user"]')
        L.append('if meta["backup_type"] == "full":')
        L.append('    out["has_system_repo"] = meta.get("has_system_repo", False)')
        L.append('    out["has_user_repo"] = meta.get("has_user_repo", False)')
        L.append('    if out["has_system_repo"]:')
        L.append('        out["system_size"] = int(sizes.get("system", 0) * BUF)')
        L.append('    if out["has_user_repo"]:')
        L.append('        out["user_size"] = int(sizes.get("user", 0) * BUF)')
        L.append('apps_out = []')
        L.append('for app in meta["apps"]:')
        L.append('    a = {"id": app["id"], "name": app["name"], "has_data": app["has_data"]}')
        L.append('    if app["has_data"]:')
        L.append('        a["data_size"] = int(sizes.get(app["id"], 0) * BUF)')
        L.append('    else:')
        L.append('        a["data_size"] = 0')
        L.append('    apps_out.append(a)')
        L.append('out["apps"] = apps_out')
        L.append('with open(out_path, "w") as f:')
        L.append('    json.dump(out, f, indent=2, ensure_ascii=False)')
        L.append('PYEOF')
        L.append('')

        L.append('printf "\\r\\033[K"')
        L.append(f'echo -e "{C_GREEN}✅ Все архивы проверены, файл манифеста создан, готово.{C_RESET}"')
        L.append('echo ""')
        L.append(f'_TOTAL_SIZE=$(du -sh "{t}" 2>/dev/null | cut -f1)')
        L.append(f'echo -e "{C_CYAN}Размер бэкапа: $_TOTAL_SIZE{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}Путь: {t}{C_RESET}"')
        L.append('echo ""')
        L.append(f'echo -e "{C_YELLOW}Нажмите любую клавишу для выхода...{C_RESET}"')
        L.append('read -n1')
        L.append('')

        return '\n'.join(L)

    # --- завершение worker'а ---

    def _on_worker_finished(self):
        manifest = os.path.join(self._target_dir, 'manifest.json') if self._target_dir else None
        manifest_ok = manifest is not None and os.path.exists(manifest)

        if not manifest_ok:
            ret = QMessageBox.question(
                self, "Бэкап прерван",
                "Создание бэкапа прервано, архив повреждён и будет удалён.\n\n"
                "Удалить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if ret == QMessageBox.StandardButton.Yes and self._target_dir:
                try:
                    shutil.rmtree(self._target_dir, ignore_errors=True)
                except Exception:
                    pass

        self._cleanup_temp()
        self._lock_ui(False)
        self._update_create_enabled()
        self.worker = None

    def _cleanup_temp(self):
        if self._temp_dir and os.path.isdir(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass
        self._temp_dir = None

    # --- блокировка ---

    def _lock_ui(self, locked):
        for w in (self.radio_full, self.radio_data, self.radio_list,
                  self.tree_backup, self.tree_list,
                  self.btn_select_all, self.btn_select_none,
                  self.btn_apply, self.btn_create):
            w.setEnabled(not locked)
