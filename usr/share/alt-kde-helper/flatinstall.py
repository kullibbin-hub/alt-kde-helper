# flatinstall.py - страница установки / восстановления Flatpak

import os
import json
import time
import shutil
import tempfile
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QButtonGroup,
    QPushButton, QTreeWidget, QTreeWidgetItem, QFileDialog, QApplication,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from flatcommon import (
    run_in_konsole, parse_install_script, get_installed_apps,
    get_running_apps, du_sb, df_free, human_size, format_sizes,
    same_fs,
    C_CYAN, C_YELLOW, C_GREEN, C_RED, C_RESET,
)
from config import get_scripts_dir
from busy import BUSY


def _kd_error(text):
    subprocess.run(['kdialog', '--error', text], check=False)


def _kd_yesno(text):
    return subprocess.run(['kdialog', '--yesno', text], check=False).returncode == 0


def _kd_msgbox(text):
    subprocess.run(['kdialog', '--msgbox', text], check=False)


_RESTORE_PREFLIGHT_WARNING = (
    "Настоятельно рекомендуется закрыть все программы.\n\n"
    "Закройте все torrent-качалки.\n\n"
    "Если у Вас мало места на дисках — очень желательно выполнить очистку:\n"
    "пункты «Очистка кэша» и «Очистка данных удалённых Flatpak-приложений»\n"
    "в разделе «Обслуживание» данной программы. После этого можно начать\n"
    "восстановление из бэкапа.\n\n"
    "Все готово?"
)


def _bash_dquote(s):
    """Экранирует строку для вставки внутрь двойных кавычек в bash."""
    return (s.replace('\\', '\\\\')
             .replace('"', '\\"')
             .replace('$', '\\$')
             .replace('`', '\\`'))


class Loader(QThread):
    """Читает .sh-скрипт или manifest.json из папки архива + список установленных."""
    data_ready = pyqtSignal(dict)
    error = pyqtSignal(str, str)  # (code, human_text)

    def __init__(self, kind, path):
        super().__init__()
        self.kind = kind  # 'script' | 'archive'
        self.path = path

    def run(self):
        try:
            installed = get_installed_apps()
            if self.kind == 'script':
                apps = parse_install_script(self.path)
                self.data_ready.emit({'apps': apps, 'installed': installed})
            else:
                manifest_path = os.path.join(self.path, 'manifest.json')
                if not os.path.exists(manifest_path):
                    self.error.emit('manifest_missing', '')
                    return
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                except Exception as e:
                    self.error.emit('manifest_broken', str(e))
                    return
                self.data_ready.emit({'manifest': manifest, 'installed': installed})
        except Exception as e:
            self.error.emit('generic', str(e))


class FlatpakInstallPage(QWidget):
    MODE_FILE = 'file'
    MODE_POPULAR = 'popular'
    MODE_ARCHIVE_DATA = 'archive_data'
    MODE_ARCHIVE_FULL = 'archive_full'

    def __init__(self, parent=None):
        super().__init__(parent)

        self._mode = self.MODE_FILE
        self._selected_path = None
        self._loaded = None
        self._loader = None
        self._worker = None
        self._temp_dir = None
        self._loading = False
        self._load_failed = False

        layout = QVBoxLayout()

        # --- Источник ---
        src_title = QLabel("Источник:")
        src_title.setStyleSheet("font-weight: bold;")
        layout.addWidget(src_title)

        src_layout = QVBoxLayout()
        self.radio_file = QRadioButton("Из списка для установки (.sh)")
        self.radio_popular = QRadioButton("Из списка популярных программ (встроенный)")
        self.radio_archive_data = QRadioButton("Из архива — восстановить данные приложений")
        self.radio_archive_full = QRadioButton("Из архива — полное восстановление (все программы + данные, без выбора)")
        self.radio_file.setChecked(True)
        self.src_group = QButtonGroup(self)
        for r in (self.radio_file, self.radio_popular,
                  self.radio_archive_data, self.radio_archive_full):
            self.src_group.addButton(r)
            src_layout.addWidget(r)
        layout.addLayout(src_layout)
        layout.addSpacing(8)

        # --- Строка выбора файла/папки ---
        choose_row = QHBoxLayout()
        self.source_label = QLabel("Файл не выбран")
        self.source_label.setWordWrap(True)
        choose_row.addWidget(self.source_label, 1)
        self.btn_choose = QPushButton("Выбрать файл")
        self.btn_choose.setIcon(QIcon.fromTheme("document-open"))
        self.btn_choose.setProperty("class", "BottomButton")
        self.btn_choose.clicked.connect(self._on_choose_source)
        choose_row.addWidget(self.btn_choose)
        layout.addLayout(choose_row)
        layout.addSpacing(4)

        # --- Дерево ---
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.tree, 1)

        # --- Label размеров ---
        self.size_label = QLabel()
        self.size_label.setWordWrap(True)
        self.size_label.setVisible(False)
        layout.addWidget(self.size_label)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_none = QPushButton("Снять выбор")
        self.btn_apply = QPushButton("Применить")
        self.btn_apply.setIcon(QIcon.fromTheme("dialog-ok"))
        for b in (self.btn_select_all, self.btn_select_none, self.btn_apply):
            b.setProperty("class", "BottomButton")

        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_select_none)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # --- Коннекты ---
        self.radio_file.toggled.connect(self._on_mode_changed)
        self.radio_popular.toggled.connect(self._on_mode_changed)
        self.radio_archive_data.toggled.connect(self._on_mode_changed)
        self.radio_archive_full.toggled.connect(self._on_mode_changed)
        self.btn_select_all.clicked.connect(self._on_select_all)
        self.btn_select_none.clicked.connect(self._on_select_none)
        self.btn_apply.clicked.connect(self._on_apply)

        BUSY.changed.connect(self._on_busy_changed)

        self._apply_mode_state()

    # ---------- определение режима ----------

    def _current_mode(self):
        if self.radio_popular.isChecked():
            return self.MODE_POPULAR
        if self.radio_archive_data.isChecked():
            return self.MODE_ARCHIVE_DATA
        if self.radio_archive_full.isChecked():
            return self.MODE_ARCHIVE_FULL
        return self.MODE_FILE

    def _on_mode_changed(self):
        if not self.sender().isChecked():
            return
        new_mode = self._current_mode()
        if new_mode == self._mode:
            return
        self._mode = new_mode
        self._selected_path = None
        self._loaded = None
        self.tree.clear()
        self._apply_mode_state()

    def _apply_mode_state(self):
        m = self._mode

        # Текст источника и кнопки
        if m == self.MODE_FILE:
            self.source_label.setText("Файл не выбран")
            self.source_label.setToolTip("")
            self.btn_choose.setText("Выбрать файл")
            self.btn_choose.setVisible(True)
        elif m == self.MODE_POPULAR:
            popular_path = os.path.join(get_scripts_dir(), 'flatinstall.sh')
            self.source_label.setText("Встроенный список: flatinstall.sh")
            self.source_label.setToolTip(popular_path)
            self.btn_choose.setVisible(False)
            self._start_load('script', popular_path)
        elif m == self.MODE_ARCHIVE_DATA:
            self.source_label.setText("Архив не выбран")
            self.source_label.setToolTip("")
            self.btn_choose.setText("Выбрать папку")
            self.btn_choose.setVisible(True)
        elif m == self.MODE_ARCHIVE_FULL:
            self.source_label.setText("Архив не выбран")
            self.source_label.setToolTip("")
            self.btn_choose.setText("Выбрать папку")
            self.btn_choose.setVisible(True)

        # Заголовки колонок
        # Ширина таблицы во всех режимах = 850
        if m in (self.MODE_FILE, self.MODE_POPULAR):
            self.tree.setColumnCount(3)
            self.tree.setHeaderLabels(["Выбор", "Название (ID)", "Описание"])
            self.tree.setColumnWidth(0, 70)
            self.tree.setColumnWidth(1, 400)
            self.tree.setColumnWidth(2, 380)
        elif m == self.MODE_ARCHIVE_DATA:
            self.tree.setColumnCount(2)
            self.tree.setHeaderLabels(["Выбор", "Приложение"])
            self.tree.setColumnWidth(0, 70)
            self.tree.setColumnWidth(1, 780)
        else:  # ARCHIVE_FULL
            self.tree.setColumnCount(1)
            self.tree.setHeaderLabels(["Приложение"])
            self.tree.setColumnWidth(0, 850)

        # Видимость select all/none и size_label
        show_select = m in (self.MODE_FILE, self.MODE_POPULAR, self.MODE_ARCHIVE_DATA)
        self.btn_select_all.setVisible(show_select)
        self.btn_select_none.setVisible(show_select)
        self.size_label.setVisible(m in (self.MODE_ARCHIVE_DATA, self.MODE_ARCHIVE_FULL))
        self.size_label.setText("")

        self._lock_ui(self._loading)
        self._update_apply_enabled()

    # ---------- BUSY ----------

    def _on_busy_changed(self, busy):
        self._update_apply_enabled()

    def _update_apply_enabled(self):
        can = (not self._loading) and (not BUSY.is_busy()) and (self._loaded is not None)
        self.btn_apply.setEnabled(can)

    # ---------- загрузка ----------

    def _on_choose_source(self):
        if self._mode == self.MODE_FILE:
            path, _ = QFileDialog.getOpenFileName(
                self, "Выберите скрипт установки",
                os.path.expanduser('~/'),
                "Скрипт (*.sh)",
                options=QFileDialog.Option.DontUseNativeDialog,
            )
            if not path:
                return
            self._selected_path = path
            self.source_label.setText(f"Файл: {os.path.basename(path)}")
            self.source_label.setToolTip(path)
            self._start_load('script', path)
        else:  # ARCHIVE_DATA или ARCHIVE_FULL
            # Нативный диалог KDE: только папки, дерево, без файлов
            path = QFileDialog.getExistingDirectory(
                self, "Выберите папку архива",
                os.path.expanduser('~/'),
                options=QFileDialog.Option.ShowDirsOnly,
            )
            if not path:
                return
            self._selected_path = path
            self.source_label.setText(f"Архив: {os.path.basename(path)}")
            self.source_label.setToolTip(path)
            self._start_load('archive', path)

    def _start_load(self, kind, path):
        if self._loader is not None and self._loader.isRunning():
            return
        self._loading = True
        self._load_failed = False
        self._loaded = None
        self.tree.clear()
        self.size_label.setText("")
        self.btn_apply.setEnabled(False)
        self._lock_ui(True)
        self.source_label.setText(self.source_label.text() + " — загрузка...")

        self._loader = Loader(kind, path)
        self._loader.data_ready.connect(self._on_data_ready)
        self._loader.error.connect(self._on_load_error)
        self._loader.finished.connect(self._on_loader_finished)
        self._loader.start()

    def _on_loader_finished(self):
        self._loading = False
        self._lock_ui(False)
        self._update_apply_enabled()
        if self._load_failed:
            return
        # Возвращаем нормальный текст вместо "— загрузка..."
        if self._mode == self.MODE_POPULAR:
            self.source_label.setText("Встроенный список: flatinstall.sh")
        elif self._mode == self.MODE_FILE and self._selected_path:
            self.source_label.setText(f"Файл: {os.path.basename(self._selected_path)}")
        elif self._mode in (self.MODE_ARCHIVE_DATA, self.MODE_ARCHIVE_FULL) and self._selected_path:
            self.source_label.setText(f"Архив: {os.path.basename(self._selected_path)}")

    def _on_load_error(self, code, text):
        self._load_failed = True
        if code == 'manifest_missing':
            _kd_error("Данный архив повреждён при архивации (отсутствует manifest.json).")
        elif code == 'manifest_broken':
            _kd_error(f"Не удалось прочитать manifest.json:\n{text}")
        else:
            _kd_error(f"Ошибка загрузки:\n{text}")
        self._loaded = None
        self.tree.clear()
        self.source_label.setText("Источник не загружен")
        self.source_label.setToolTip("")
        self.btn_apply.setEnabled(False)

    def _on_data_ready(self, payload):
        if 'apps' in payload:
            self._loaded = payload
            self._populate_script_tree(payload['apps'], payload['installed'])
        else:
            manifest = payload['manifest']
            backup_type = manifest.get('backup_type', '')
            if self._mode == self.MODE_ARCHIVE_FULL and backup_type != 'full':
                _kd_error("В данном архиве нет файлов программ, только данные.\n"
                          "Для восстановления данных используйте пункт\n"
                          "«Из архива — восстановить данные приложений».")
                self._loaded = None
                self.tree.clear()
                self.btn_apply.setEnabled(False)
                return
            self._loaded = payload
            if self._mode == self.MODE_ARCHIVE_DATA:
                self._populate_data_tree(manifest, payload['installed'])
            else:
                self._populate_full_tree(manifest)

    # ---------- наполнение дерева ----------

    def _populate_script_tree(self, apps, installed):
        self.tree.clear()

        categories = []
        for entry in apps:
            cat = entry.get('category')
            if categories and categories[-1][0] == cat:
                categories[-1][1].append(entry)
            else:
                categories.append((cat, [entry]))

        bold = QFont()
        bold.setBold(True)

        for cat_name, entries in categories:
            if cat_name:
                header = QTreeWidgetItem(["", cat_name, ""])
                header.setFont(1, bold)
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                header.setData(0, Qt.ItemDataRole.UserRole, None)
                header.setData(0, Qt.ItemDataRole.UserRole + 1, 'category')
                self.tree.addTopLevelItem(header)
                parent = header
                header.setExpanded(True)
            else:
                parent = self.tree.invisibleRootItem()

            entries_sorted = sorted(entries, key=lambda e: e['name'].lower())
            for entry in entries_sorted:
                app_id = entry['app_id']
                name = entry['name']
                desc = entry.get('desc') or ''
                display = f"{name} ({app_id})" if name != app_id else app_id
                is_installed = app_id in installed
                desc_text = desc + (" (установлено)" if is_installed else "")

                item = QTreeWidgetItem(["", display, desc_text])
                item.setData(0, Qt.ItemDataRole.UserRole, app_id)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, 'app')
                if is_installed:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                else:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                                   | Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                parent.addChild(item) if parent is not self.tree.invisibleRootItem() \
                    else self.tree.addTopLevelItem(item)

    def _populate_data_tree(self, manifest, installed):
        self.tree.clear()
        apps = manifest.get('apps', [])
        filtered = [a for a in apps if a.get('has_data') and a.get('id') in installed]
        filtered.sort(key=lambda a: a.get('name', a['id']).lower())

        if not filtered:
            _kd_msgbox("В архиве нет данных для установленных приложений.")
            self._loaded = None
            self.btn_apply.setEnabled(False)
            return

        for a in filtered:
            app_id = a['id']
            name = a.get('name', app_id)
            display = f"{name} ({app_id})" if name != app_id else app_id
            item = QTreeWidgetItem(["", display])
            item.setData(0, Qt.ItemDataRole.UserRole, app_id)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, 'app')
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            self.tree.addTopLevelItem(item)

        self.tree.itemChanged.connect(self._on_data_tree_changed)
        self._update_data_label()

    def _populate_full_tree(self, manifest):
        self.tree.clear()
        apps = manifest.get('apps', [])
        apps_sorted = sorted(apps, key=lambda a: a.get('name', a['id']).lower())

        for a in apps_sorted:
            app_id = a['id']
            name = a.get('name', app_id)
            display = f"{name} ({app_id})" if name != app_id else app_id
            item = QTreeWidgetItem([display])
            item.setData(0, Qt.ItemDataRole.UserRole, app_id)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, 'app')
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tree.addTopLevelItem(item)

        self._update_full_label(manifest)

    def _on_data_tree_changed(self, item, column):
        if column == 0 and self._mode == self.MODE_ARCHIVE_DATA:
            self._update_data_label()

    def _update_data_label(self):
        if self._mode != self.MODE_ARCHIVE_DATA or not self._loaded:
            return
        manifest = self._loaded['manifest']
        by_id = {a['id']: a for a in manifest.get('apps', [])}
        total = 0
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                app_id = item.data(0, Qt.ItemDataRole.UserRole)
                total += by_id.get(app_id, {}).get('data_size', 0)
        self.size_label.setText(f"Размер выбранных данных: ~{human_size(total)}")

    def _update_full_label(self, manifest):
        parts = []
        has_sys = manifest.get('has_system_repo', False)
        has_usr = manifest.get('has_user_repo', False)
        sys_sz = manifest.get('system_size', 0)
        usr_sz = manifest.get('user_size', 0)
        data_sz = sum(a.get('data_size', 0) for a in manifest.get('apps', []) if a.get('has_data'))

        home = os.path.expanduser('~')
        same = same_fs('/', home)

        if same:
            total = (sys_sz if has_sys else 0) + (usr_sz if has_usr else 0) + data_sz
            parts.append(f"Программы и данные: ~{human_size(total)}")
        else:
            prog_root = sys_sz if has_sys else 0
            prog_home = (usr_sz if has_usr else 0) + data_sz
            parts.append(f"На разделе /: ~{human_size(prog_root)}")
            parts.append(f"На разделе home: ~{human_size(prog_home)}")

        self.size_label.setText("\n".join(parts))

    # ---------- выбор ----------

    def _iter_app_items(self):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.data(0, Qt.ItemDataRole.UserRole + 1) == 'category':
                for j in range(top.childCount()):
                    yield top.child(j)
            elif top.data(0, Qt.ItemDataRole.UserRole + 1) == 'app':
                yield top

    def _on_select_all(self):
        self.tree.blockSignals(True)
        for item in self._iter_app_items():
            if not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
                continue
            col = 0
            item.setCheckState(col, Qt.CheckState.Checked)
        self.tree.blockSignals(False)
        if self._mode == self.MODE_ARCHIVE_DATA:
            self._update_data_label()

    def _on_select_none(self):
        self.tree.blockSignals(True)
        for item in self._iter_app_items():
            if not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
                continue
            col = 0
            item.setCheckState(col, Qt.CheckState.Unchecked)
        self.tree.blockSignals(False)
        if self._mode == self.MODE_ARCHIVE_DATA:
            self._update_data_label()

    # ---------- применить ----------

    def _on_apply(self):
        if not self._loaded or BUSY.is_busy():
            return
        if self._mode in (self.MODE_FILE, self.MODE_POPULAR):
            self._apply_install()
        elif self._mode == self.MODE_ARCHIVE_DATA:
            self._apply_data_restore()
        elif self._mode == self.MODE_ARCHIVE_FULL:
            self._apply_full_restore()

    # ---- установка из .sh ----

    def _apply_install(self):
        selected = []
        for item in self._iter_app_items():
            if item.checkState(0) == Qt.CheckState.Checked:
                app_id = item.data(0, Qt.ItemDataRole.UserRole)
                name = self._name_from_display(item.text(1))
                selected.append((app_id, name))
        if not selected:
            _kd_error("Не выбрано ни одного приложения.")
            return
        selected.sort(key=lambda x: x[1].lower())

        script = self._build_install_script(selected)
        try:
            temp_dir = tempfile.mkdtemp(prefix='alt-flatinstall-')
            self._temp_dir = temp_dir
            sp = os.path.join(temp_dir, 'install.sh')
            with open(sp, 'w', encoding='utf-8') as f:
                f.write(script)
            os.chmod(sp, 0o755)
        except Exception as e:
            self._cleanup_temp()
            _kd_error(f"Не удалось подготовить установку:\n{e}")
            return

        self._lock_ui(True)
        self.btn_apply.setEnabled(False)
        self._worker = run_in_konsole(sp, "Установка Flatpak", self._on_worker_finished, parent=self)

    def _name_from_display(self, text):
        if ' (' in text and text.endswith(')'):
            return text.rsplit(' (', 1)[0]
        return text

    def _build_install_script(self, selected):
        L = ['#!/bin/bash', '']
        L.append(f'echo -e "{C_CYAN}========================================{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}Установка приложений Flatpak ({len(selected)}){C_RESET}"')
        L.append(f'echo -e "{C_CYAN}========================================{C_RESET}"')
        L.append('')
        for app_id, name in selected:
            L.append(f'echo -e "{C_YELLOW}→ {_bash_dquote(name)} ({_bash_dquote(app_id)})...{C_RESET}"')
            L.append(f'flatpak install -y flathub {app_id}')
        L.append('')
        L.append(f'echo ""')
        L.append(f'echo -e "{C_YELLOW}→ Проверка установки...{C_RESET}"')
        L.append('INSTALLED_LIST=$(flatpak list --app --columns=application)')
        L.append('FAILED_NAMES=""')
        for app_id, name in selected:
            L.append(f'if ! echo "$INSTALLED_LIST" | grep -qx "{app_id}"; then')
            L.append(f'    echo -e "{C_RED}  ✗ {_bash_dquote(name)}{C_RESET}"')
            L.append(f'    FAILED_NAMES="$FAILED_NAMES  • {_bash_dquote(name)}\\n"')
            L.append('fi')
        L.append('')
        L.append('if [ -n "$FAILED_NAMES" ]; then')
        L.append(f'    echo ""')
        L.append(f'    echo -e "{C_YELLOW}Не все приложения установлены:{C_RESET}"')
        L.append('    printf "%b" "$FAILED_NAMES"')
        L.append(f'    echo -e "{C_YELLOW}Можно закрыть терминал и нажать «Применить» ещё раз —{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}уже установленные приложения не будут скачаны повторно.{C_RESET}"')
        L.append('else')
        L.append(f'    echo -e "{C_GREEN}✅ Все приложения установлены успешно.{C_RESET}"')
        L.append('fi')
        L.append('')
        L.append(f'echo -e "{C_YELLOW}→ Обновление меню и иконок KDE...{C_RESET}"')
        L.append('rm -f ~/.cache/icon-cache.kcache')
        L.append('if command -v kbuildsycoca6 >/dev/null 2>&1; then')
        L.append('    kbuildsycoca6 --noincremental 2>/dev/null || true')
        L.append('fi')
        L.append('if command -v update-desktop-database >/dev/null 2>&1; then')
        L.append('    update-desktop-database ~/.local/share/flatpak/exports/share/applications 2>/dev/null || true')
        L.append('    update-desktop-database /var/lib/flatpak/exports/share/applications 2>/dev/null || true')
        L.append('fi')
        L.append('')
        L.append(f'echo -e "{C_YELLOW}Нажмите любую клавишу для выхода...{C_RESET}"')
        L.append('read -n1')
        return '\n'.join(L)

    # ---- восстановление данных ----

    def _apply_data_restore(self):
        manifest = self._loaded['manifest']
        by_id = {a['id']: a for a in manifest.get('apps', [])}
        selected = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                app_id = item.data(0, Qt.ItemDataRole.UserRole)
                if app_id in by_id:
                    selected.append(by_id[app_id])
        if not selected:
            _kd_error("Не выбрано ни одного приложения.")
            return

        home = os.path.expanduser('~')
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            need = sum(a.get('data_size', 0) for a in selected)
            freed = sum(du_sb(os.path.expanduser(f'~/.var/app/{a["id"]}')) for a in selected)
            require = max(0, need - freed)
            free = df_free(home)
        finally:
            QApplication.restoreOverrideCursor()
        if require > free:
            _kd_error(f"Недостаточно свободного места в домашнем разделе.\n\n"
                      f"Требуется: ~{human_size(require)}\n"
                      f"Свободно: {human_size(free)}")
            return

        selected_ids = {a['id'] for a in selected}
        running = get_running_apps() & selected_ids

        if running:
            names = ', '.join(by_id[a].get('name', a) for a in running)
            preflight = (f"Следующие приложения Flatpak запущены и будут закрыты для восстановления:\n"
                         f"{names}\n\n" + _RESTORE_PREFLIGHT_WARNING)
        else:
            preflight = _RESTORE_PREFLIGHT_WARNING

        if not _kd_yesno(preflight):
            return

        if running:
            for app_id in running:
                subprocess.run(['flatpak', 'kill', app_id], check=False)
            time.sleep(1)
            running2 = get_running_apps() & selected_ids
            if running2:
                names2 = '\n'.join(f'  • {by_id[a].get("name", a)}' for a in running2)
                _kd_error(f"Не удалось закрыть приложения:\n{names2}\n\n"
                          f"Закройте их вручную и нажмите «Применить» снова.")
                return

        archive_dir = self._selected_path
        script = self._build_data_restore_script(archive_dir, selected)
        try:
            temp_dir = tempfile.mkdtemp(prefix='alt-flatrestore-')
            self._temp_dir = temp_dir
            sp = os.path.join(temp_dir, 'restore_data.sh')
            with open(sp, 'w', encoding='utf-8') as f:
                f.write(script)
            os.chmod(sp, 0o755)
        except Exception as e:
            self._cleanup_temp()
            _kd_error(f"Не удалось подготовить восстановление:\n{e}")
            return

        self._lock_ui(True)
        self.btn_apply.setEnabled(False)
        self._worker = run_in_konsole(sp, "Восстановление данных Flatpak",
                                       self._on_worker_finished, parent=self)

    def _build_data_restore_script(self, archive_dir, selected):
        t = archive_dir
        total_bytes = sum(a.get('data_size', 0) for a in selected)
        ids_csv = ' '.join(a['id'] for a in selected)
        rm_targets = ' '.join(f'~/.var/app/{a["id"]}' for a in selected)

        L = ['#!/bin/bash', '']
        L.append('fmt_size() {')
        L.append('    local b=$1')
        L.append('    if [ "$b" -ge 1073741824 ]; then')
        L.append('        awk -v b="$b" \'BEGIN{printf "%.1f ГБ", b/1073741824}\'')
        L.append('    elif [ "$b" -ge 1048576 ]; then')
        L.append('        awk -v b="$b" \'BEGIN{printf "%.1f МБ", b/1048576}\'')
        L.append('    elif [ "$b" -ge 1024 ]; then')
        L.append('        awk -v b="$b" \'BEGIN{printf "%.1f КБ", b/1024}\'')
        L.append('    else')
        L.append('        echo "${b} Б"')
        L.append('    fi')
        L.append('}')
        L.append('')
        L.append(f'echo -e "{C_CYAN}========================================{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}Восстановление данных приложений ({len(selected)}){C_RESET}"')
        L.append(f'echo -e "{C_CYAN}========================================{C_RESET}"')
        L.append('')

        L.append(f'echo -e "{C_YELLOW}→ Проверка целостности архива данных...{C_RESET}"')
        L.append('CHECK_FAILED=0')
        L.append(f'if [ ! -f "{t}/data.tar.zst" ]; then')
        L.append(f'    echo -e "{C_RED}  data.tar.zst — файл отсутствует{C_RESET}"')
        L.append('    CHECK_FAILED=1')
        L.append('else')
        L.append('    echo -n "  data.tar.zst ... "')
        L.append(f'    if tar -I \'zstd -d -T0\' -tf "{t}/data.tar.zst" >/dev/null 2>&1; then')
        L.append('        echo "ok"')
        L.append('    else')
        L.append(f'        echo -e "{C_RED}повреждён{C_RESET}"')
        L.append('        CHECK_FAILED=1')
        L.append('    fi')
        L.append('fi')
        L.append('if [ "$CHECK_FAILED" -ne 0 ]; then')
        L.append(f'    echo ""')
        L.append(f'    echo -e "{C_RED}Архив данных повреждён или отсутствует. Восстановление отменено.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Данные приложений не тронуты.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Нажмите любую клавишу для выхода...{C_RESET}"')
        L.append('    read -n1')
        L.append('    exit 1')
        L.append('fi')
        L.append('')

        L.append(f'echo -e "{C_YELLOW}⚠ Не закрывайте это окно до конца процесса, иначе придется его повторить.{C_RESET}"')
        L.append('')

        L.append(f'echo -e "{C_YELLOW}→ Удаление текущих данных выбранных приложений...{C_RESET}"')
        L.append(f'rm -rf {rm_targets}')
        L.append('')
        L.append(f'echo -e "{C_YELLOW}→ Распаковка данных в ~/.var/app...{C_RESET}"')
        L.append(f'TOTAL={total_bytes}')
        L.append('if [ "$TOTAL" -le 0 ]; then TOTAL=1; fi')
        L.append('(')
        L.append('    while true; do')
        L.append('        CUR=0')
        for a in selected:
            L.append(f'        if [ -d ~/.var/app/{a["id"]} ]; then _s=$(du -sb ~/.var/app/{a["id"]} 2>/dev/null | cut -f1); CUR=$((CUR + ${{_s:-0}})); fi')
        L.append('        PCT=$((CUR * 100 / TOTAL))')
        L.append('        if [ "$PCT" -gt 100 ]; then PCT=100; fi')
        L.append('        printf "\\r\\033[K   Восстановлено: %d%% (%s / %s)" "$PCT" "$(fmt_size $CUR)" "$(fmt_size $TOTAL)"')
        L.append('        sleep 5')
        L.append('    done')
        L.append(') &')
        L.append('MONITOR=$!')
        L.append('')
        L.append(f'tar -I \'zstd -d -T0\' -xf "{t}/data.tar.zst" -C ~/.var/app {ids_csv}')
        L.append('TAR_RC=$?')
        L.append('kill $MONITOR 2>/dev/null')
        L.append('wait $MONITOR 2>/dev/null')
        L.append('if [ "$TAR_RC" -eq 0 ]; then')
        L.append('    printf "\\r\\033[K   Восстановлено: 100%% (%s / %s)\\n" "$(fmt_size $TOTAL)" "$(fmt_size $TOTAL)"')
        L.append('else')
        L.append('    printf "\\r\\033[K"')
        L.append('fi')
        L.append('')
        L.append('if [ "$TAR_RC" -ne 0 ]; then')
        L.append('    MISSING=""')
        for a in selected:
            L.append(f'    if [ ! -d ~/.var/app/{a["id"]} ]; then MISSING="$MISSING {_bash_dquote(a.get("name", a["id"]))}"; fi')
        L.append(f'    echo -e "{C_RED}❌ Распаковка не завершена.{C_RESET}"')
        L.append('    if [ -n "$MISSING" ]; then')
        L.append(f'        echo -e "{C_YELLOW}   Не восстановились:$MISSING{C_RESET}"')
        L.append('    fi')
        L.append(f'    echo ""')
        L.append(f'    echo -e "{C_YELLOW}Наиболее вероятная причина — нехватка свободного места на диске:{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}какая-то программа скачивает или создаёт файлы, которые заняли место.{C_RESET}"')
        L.append(f'    echo -e "{C_CYAN}Ваш архив цел. Перезагрузите компьютер и повторите восстановление.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Нажмите любую клавишу для выхода...{C_RESET}"')
        L.append('    read -n1')
        L.append('    exit 1')
        L.append('fi')
        L.append('')
        L.append(f'echo -e "{C_GREEN}✅ Восстановление данных завершено.{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}Источник: {t}{C_RESET}"')
        L.append('echo ""')
        L.append(f'echo -e "{C_YELLOW}Нажмите любую клавишу для выхода...{C_RESET}"')
        L.append('read -n1')
        return '\n'.join(L)

    # ---- полное восстановление ----

    def _apply_full_restore(self):
        manifest = self._loaded['manifest']

        home = os.path.expanduser('~')
        has_sys = manifest.get('has_system_repo', False)
        has_usr = manifest.get('has_user_repo', False)
        sys_sz = manifest.get('system_size', 0) if has_sys else 0
        usr_sz = manifest.get('user_size', 0) if has_usr else 0
        data_sz = sum(a.get('data_size', 0) for a in manifest.get('apps', []) if a.get('has_data'))

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            freed_sys = du_sb('/var/lib/flatpak') if has_sys else 0
            freed_usr = du_sb(os.path.expanduser('~/.local/share/flatpak')) if has_usr else 0
            freed_data = sum(
                du_sb(os.path.expanduser(f'~/.var/app/{a["id"]}'))
                for a in manifest.get('apps', []) if a.get('has_data')
            )
            need_root = max(0, sys_sz - freed_sys)
            need_home = max(0, (usr_sz + data_sz) - (freed_usr + freed_data))
            same = same_fs('/', home)
            if same:
                total_need = need_root + need_home
                free_home = df_free(home)
                free_root = None
            else:
                free_root = df_free('/')
                free_home = df_free(home)
        finally:
            QApplication.restoreOverrideCursor()

        if same:
            if total_need > free_home:
                _kd_error(f"Недостаточно свободного места.\n\n"
                          f"Требуется: ~{human_size(total_need)}\n"
                          f"Свободно: {human_size(free_home)}")
                return
        else:
            if need_root > free_root or need_home > free_home:
                _kd_error(
                    f"Недостаточно свободного места.\n\n"
                    f"На разделе /: нужно ~{human_size(need_root)}, "
                    f"свободно {human_size(free_root)}\n"
                    f"На разделе home: нужно ~{human_size(need_home)}, "
                    f"свободно {human_size(free_home)}"
                )
                return

        running = get_running_apps()

        preflight = (
            "Полное восстановление заменит системные Flatpak-программы для   \n"
            "ВСЕХ пользователей компьютера, вернув их к версиям из бэкапа.   \n"
            "Настройки и данные приложений восстановятся ТОЛЬКО для\n"
            "текущего пользователя.\n\n"
            "У других пользователей данные останутся без изменений, но старые   \n"
            "версии программ могут оказаться несовместимы с их профилями.   \n"
            "Для восстановления нормальной работы потребуется обновить   \n"
            "программы через интернет.\n\n"
            "Приложения, установленные после создания бэкапа, будут удалены,   \n"
            "но их пользовательские данные сохранятся. После повторной   \n"
            "установки приложения смогут использовать прежние настройки.   \n\n"
            "Перед восстановлением закройте все программы и торренты.   \n"
            "Если мало места, освободите его заранее (см. пункт\n"
            "«Очистка кэша» в разделе «Обслуживание»).\n\n"
        )

        if running:
            names = ', '.join(sorted(running))
            preflight += f"Следующие запущенные приложения будут закрыты:\n{names}\n\n"

        preflight += "Продолжить?"

        if not _kd_yesno(preflight):
            return

        if running:
            for app_id in running:
                subprocess.run(['flatpak', 'kill', app_id], check=False)
            time.sleep(1)
            running2 = get_running_apps()
            if running2:
                names2 = '\n'.join(f'  • {a}' for a in running2)
                _kd_error(f"Не удалось закрыть приложения:\n{names2}\n\n"
                          f"Закройте их вручную и нажмите «Применить» снова.")
                return

        archive_dir = self._selected_path
        script = self._build_full_restore_script(archive_dir, manifest)
        try:
            temp_dir = tempfile.mkdtemp(prefix='alt-flatrestore-')
            self._temp_dir = temp_dir
            sp = os.path.join(temp_dir, 'restore_full.sh')
            with open(sp, 'w', encoding='utf-8') as f:
                f.write(script)
            os.chmod(sp, 0o755)
        except Exception as e:
            self._cleanup_temp()
            _kd_error(f"Не удалось подготовить восстановление:\n{e}")
            return

        self._lock_ui(True)
        self.btn_apply.setEnabled(False)
        self._worker = run_in_konsole(sp, "Полное восстановление Flatpak",
                                       self._on_worker_finished, parent=self)

    def _build_full_restore_script(self, archive_dir, manifest):
        t = archive_dir
        has_sys = manifest.get('has_system_repo', False)
        has_usr = manifest.get('has_user_repo', False)
        user_matches = (manifest.get('user', '') == os.environ.get('USER', ''))
        apps = manifest.get('apps', [])

        data_apps = [a for a in apps if a.get('has_data')]
        data_ids = ' '.join(a['id'] for a in data_apps)
        data_rm = ' '.join(f'~/.var/app/{a["id"]}' for a in data_apps)
        data_total = sum(a.get('data_size', 0) for a in data_apps) if data_apps else 0

        sys_sz = manifest.get('system_size', 0) if has_sys else 0
        usr_sz = manifest.get('user_size', 0) if has_usr else 0

        expected = []
        if has_sys:
            expected.append('flatpak-system.tar.zst')
        if has_usr:
            expected.append('flatpak-user.tar.zst')
        if data_apps:
            expected.append('data.tar.zst')

        fail_tail = [
            '    echo ""',
            f'    echo -e "{{C_YELLOW}}Наиболее вероятная причина — нехватка свободного места на диске:{{C_RESET}}"',
            f'    echo -e "{{C_YELLOW}}какая-то программа скачивает или создаёт файлы, которые заняли место.{{C_RESET}}"',
            f'    echo -e "{{C_CYAN}}Ваш архив цел. Перезагрузите компьютер и повторите восстановление.{{C_RESET}}"',
            f'    echo -e "{{C_YELLOW}}Нажмите любую клавишу для выхода...{{C_RESET}}"',
            '    read -n1',
            '    exit 1',
            'fi',
            '',
        ]

        L = ['#!/bin/bash', '']
        L.append('fmt_size() {')
        L.append('    local b=$1')
        L.append('    if [ "$b" -ge 1073741824 ]; then')
        L.append('        awk -v b="$b" \'BEGIN{printf "%.1f ГБ", b/1073741824}\'')
        L.append('    elif [ "$b" -ge 1048576 ]; then')
        L.append('        awk -v b="$b" \'BEGIN{printf "%.1f МБ", b/1048576}\'')
        L.append('    elif [ "$b" -ge 1024 ]; then')
        L.append('        awk -v b="$b" \'BEGIN{printf "%.1f КБ", b/1024}\'')
        L.append('    else')
        L.append('        echo "${b} Б"')
        L.append('    fi')
        L.append('}')
        L.append('')
        L.append(f'echo -e "{C_CYAN}========================================{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}Полное восстановление Flatpak{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}========================================{C_RESET}"')
        L.append('')

        L.append(f'echo -e "{C_YELLOW}→ Проверка целостности архивов...{C_RESET}"')
        L.append('CHECK_FAILED=0')
        for arc in expected:
            L.append(f'if [ ! -f "{t}/{arc}" ]; then')
            L.append(f'    echo -e "{C_RED}  {arc} — файл отсутствует{C_RESET}"')
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
        L.append(f'    echo -e "{C_RED}Архив повреждён или неполон. Восстановление отменено.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Текущий Flatpak не тронут.{C_RESET}"')
        L.append(f'    echo -e "{C_YELLOW}Нажмите любую клавишу для выхода...{C_RESET}"')
        L.append('    read -n1')
        L.append('    exit 1')
        L.append('fi')
        L.append('')

        L.append(f'echo -e "{C_YELLOW}⚠ Не закрывайте это окно до конца процесса, иначе придется его повторить.{C_RESET}"')
        L.append('')

        if data_apps:
            L.append(f'echo -e "{C_YELLOW}→ Удаление текущих данных приложений...{C_RESET}"')
            L.append(f'rm -rf {data_rm}')
            L.append('')
            L.append(f'echo -e "{C_YELLOW}→ Распаковка данных в ~/.var/app...{C_RESET}"')
            L.append(f'TOTAL={data_total}')
            L.append('if [ "$TOTAL" -le 0 ]; then TOTAL=1; fi')
            L.append('(')
            L.append('    while true; do')
            L.append('        CUR=0')
            for a in data_apps:
                L.append(f'        if [ -d ~/.var/app/{a["id"]} ]; then _s=$(du -sb ~/.var/app/{a["id"]} 2>/dev/null | cut -f1); CUR=$((CUR + ${{_s:-0}})); fi')
            L.append('        PCT=$((CUR * 100 / TOTAL))')
            L.append('        if [ "$PCT" -gt 100 ]; then PCT=100; fi')
            L.append('        printf "\\r\\033[K   Восстановлено: %d%% (%s / %s)" "$PCT" "$(fmt_size $CUR)" "$(fmt_size $TOTAL)"')
            L.append('        sleep 5')
            L.append('    done')
            L.append(') &')
            L.append('MONITOR=$!')
            L.append('')
            L.append(f'tar -I \'zstd -d -T0\' -xf "{t}/data.tar.zst" -C ~/.var/app {data_ids}')
            L.append('TAR_RC=$?')
            L.append('kill $MONITOR 2>/dev/null')
            L.append('wait $MONITOR 2>/dev/null')
            L.append('if [ "$TAR_RC" -eq 0 ]; then')
            L.append('    printf "\\r\\033[K   Восстановлено: 100%% (%s / %s)\\n" "$(fmt_size $TOTAL)" "$(fmt_size $TOTAL)"')
            L.append('else')
            L.append('    printf "\\r\\033[K"')
            L.append('fi')
            L.append('')
            L.append('if [ "$TAR_RC" -ne 0 ]; then')
            L.append(f'    echo -e "{C_RED}❌ Данные восстановлены не полностью.{C_RESET}"')
            L.append(f'    echo -e "{C_YELLOW}Программы Flatpak не тронуты.{C_RESET}"')
            for line in fail_tail:
                L.append(line)

        if has_sys:
            L.append(f'echo -e "{C_YELLOW}→ Удаление /var/lib/flatpak...{C_RESET}"')
            L.append('echo ""')
            L.append(f'echo -e "{C_YELLOW}Введите пароль. Символы не отображаются, но вводятся, затем Enter{C_RESET}"')
            L.append('sudo rm -rf /var/lib/flatpak')
            L.append('')
            L.append(f'echo -e "{C_YELLOW}→ Распаковка /var/lib/flatpak...{C_RESET}"')
            L.append(f'TOTAL={sys_sz}')
            L.append('if [ "$TOTAL" -le 0 ]; then TOTAL=1; fi')
            L.append('(')
            L.append('    while true; do')
            L.append('        _s=$(sudo -n du -sb /var/lib/flatpak 2>/dev/null | cut -f1)')
            L.append('        if [ -z "$_s" ]; then CUR=0; else CUR=$_s; fi')
            L.append('        PCT=$((CUR * 100 / TOTAL))')
            L.append('        if [ "$PCT" -gt 100 ]; then PCT=100; fi')
            L.append('        printf "\\r\\033[K   Восстановлено: %d%% (%s / %s)" "$PCT" "$(fmt_size $CUR)" "$(fmt_size $TOTAL)"')
            L.append('        sleep 5')
            L.append('    done')
            L.append(') &')
            L.append('MONITOR=$!')
            L.append('')
            L.append(f'sudo tar -I \'zstd -d -T0\' -xf "{t}/flatpak-system.tar.zst" -C /')
            L.append('TAR_RC=$?')
            L.append('kill $MONITOR 2>/dev/null')
            L.append('wait $MONITOR 2>/dev/null')
            L.append('if [ "$TAR_RC" -eq 0 ]; then')
            L.append('    printf "\\r\\033[K   Восстановлено: 100%% (%s / %s)\\n" "$(fmt_size $TOTAL)" "$(fmt_size $TOTAL)"')
            L.append('else')
            L.append('    printf "\\r\\033[K"')
            L.append('fi')
            L.append('')
            L.append('if [ "$TAR_RC" -ne 0 ]; then')
            L.append(f'    echo -e "{C_RED}❌ Не удалось распаковать /var/lib/flatpak.{C_RESET}"')
            L.append(f'    echo -e "{C_YELLOW}Системные программы Flatpak сейчас могут отсутствовать в меню.{C_RESET}"')
            for line in fail_tail:
                L.append(line)

        if has_usr:
            L.append(f'echo -e "{C_YELLOW}→ Удаление ~/.local/share/flatpak...{C_RESET}"')
            L.append('rm -rf ~/.local/share/flatpak')
            L.append('')
            L.append(f'echo -e "{C_YELLOW}→ Распаковка ~/.local/share/flatpak...{C_RESET}"')
            L.append(f'TOTAL={usr_sz}')
            L.append('if [ "$TOTAL" -le 0 ]; then TOTAL=1; fi')
            L.append('(')
            L.append('    while true; do')
            L.append('        _s=$(du -sb ~/.local/share/flatpak 2>/dev/null | cut -f1)')
            L.append('        if [ -z "$_s" ]; then CUR=0; else CUR=$_s; fi')
            L.append('        PCT=$((CUR * 100 / TOTAL))')
            L.append('        if [ "$PCT" -gt 100 ]; then PCT=100; fi')
            L.append('        printf "\\r\\033[K   Восстановлено: %d%% (%s / %s)" "$PCT" "$(fmt_size $CUR)" "$(fmt_size $TOTAL)"')
            L.append('        sleep 5')
            L.append('    done')
            L.append(') &')
            L.append('MONITOR=$!')
            L.append('')
            L.append(f'tar -I \'zstd -d -T0\' -xf "{t}/flatpak-user.tar.zst" -C ~/.local/share')
            L.append('TAR_RC=$?')
            L.append('kill $MONITOR 2>/dev/null')
            L.append('wait $MONITOR 2>/dev/null')
            L.append('if [ "$TAR_RC" -eq 0 ]; then')
            L.append('    printf "\\r\\033[K   Восстановлено: 100%% (%s / %s)\\n" "$(fmt_size $TOTAL)" "$(fmt_size $TOTAL)"')
            L.append('else')
            L.append('    printf "\\r\\033[K"')
            L.append('fi')
            L.append('')
            L.append('if [ "$TAR_RC" -ne 0 ]; then')
            L.append(f'    echo -e "{C_RED}❌ Не удалось распаковать ~/.local/share/flatpak.{C_RESET}"')
            L.append(f'    echo -e "{C_YELLOW}Пользовательские программы Flatpak сейчас могут отсутствовать в меню.{C_RESET}"')
            for line in fail_tail:
                L.append(line)

        if not user_matches:
            L.append(f'echo -e "{C_YELLOW}→ Пользователь в бэкапе отличается — flatpak repair...{C_RESET}"')
            L.append('flatpak repair --user 2>/dev/null || true')
            if not has_sys:
                L.append('echo ""')
                L.append(f'echo -e "{C_YELLOW}Введите пароль. Символы не отображаются, но вводятся, затем Enter{C_RESET}"')
            L.append('sudo flatpak repair 2>/dev/null || true')
            L.append('')

        L.append(f'echo -e "{C_YELLOW}→ Обновление меню и иконок KDE...{C_RESET}"')
        L.append('rm -f ~/.cache/icon-cache.kcache')
        L.append('if command -v kbuildsycoca6 >/dev/null 2>&1; then')
        L.append('    kbuildsycoca6 --noincremental 2>/dev/null || true')
        L.append('fi')
        L.append('if command -v update-desktop-database >/dev/null 2>&1; then')
        L.append('    update-desktop-database ~/.local/share/flatpak/exports/share/applications 2>/dev/null || true')
        L.append('    update-desktop-database /var/lib/flatpak/exports/share/applications 2>/dev/null || true')
        L.append('fi')
        L.append('if command -v kquitapp6 >/dev/null 2>&1 && command -v kstart >/dev/null 2>&1; then')
        L.append(f'    echo -e "{C_YELLOW}⚠ Перезапуск оболочки Plasma. Панель задач исчезнет на несколько секунд \\nи появится снова. Это не баг, подождите.{C_RESET}"')
        L.append('    sleep 3')
        L.append('    kquitapp6 plasmashell 2>/dev/null || true')
        L.append('    sleep 1')
        L.append('    kstart plasmashell 2>/dev/null || true')
        L.append('fi')
        L.append('')
        L.append(f'echo -e "{C_GREEN}✅ Полное восстановление завершено.{C_RESET}"')
        L.append(f'echo -e "{C_CYAN}Источник: {t}{C_RESET}"')
        L.append('echo ""')
        L.append(f'echo -e "{C_YELLOW}Нажмите любую клавишу для выхода...{C_RESET}"')
        L.append('read -n1')
        return '\n'.join(L)

    # ---------- завершение ----------

    def _on_worker_finished(self):
        self._cleanup_temp()
        self._lock_ui(False)
        self._update_apply_enabled()
        self._worker = None

    def _cleanup_temp(self):
        if self._temp_dir and os.path.isdir(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass
        self._temp_dir = None

    # ---------- блокировка ----------

    def _lock_ui(self, locked):
        for w in (self.radio_file, self.radio_popular,
                  self.radio_archive_data, self.radio_archive_full,
                  self.btn_choose, self.tree,
                  self.btn_select_all, self.btn_select_none,
                  self.btn_apply):
            w.setEnabled(not locked)
