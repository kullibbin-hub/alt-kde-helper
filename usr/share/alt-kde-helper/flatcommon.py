# flatcommon.py - общие утилиты для flatbackup.py и flatinstall.py

import os
import subprocess
from PyQt6.QtCore import QThread
from busy import BUSY


# ANSI-последовательности для генерации bash-скриптов (для echo -e)
C_CYAN = r'\033[1;36m'
C_YELLOW = r'\033[1;33m'
C_GREEN = r'\033[1;32m'
C_RED = r'\033[1;31m'
C_RESET = r'\033[0m'


class KonsoleWorker(QThread):
    """Запускает bash-скрипт в новом окне konsole и ждёт его завершения.
    Сигнал QThread.finished (встроенный) срабатывает, когда konsole закрыт."""

    def __init__(self, script_path, title, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.title = title
        self.process = None

    def run(self):
        BUSY.acquire()
        try:
            self.process = subprocess.Popen(
                ['konsole', '--separate', '--title', self.title, '-e', 'bash', self.script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.process.wait()
        except Exception:
            pass
        finally:
            BUSY.release()
        # QThread.finished эмитится автоматически при выходе из run()


def run_in_konsole(script_path, title, on_finished, parent=None):
    """Хелпер: создаёт KonsoleWorker, коннектит on_finished и запускает.
    Возвращает worker — вызывающий обязан сохранить его ссылку (напр. self.worker)."""
    worker = KonsoleWorker(script_path, title, parent)
    worker.finished.connect(on_finished)
    worker.start()
    return worker


def parse_desktop_name(app_id):
    """Возвращает человекочитаемое имя из .desktop файла Flatpak.
    Приоритет: Name[ru]= → Name= из секции [Desktop Entry].
    Секции [Desktop Action ...] игнорируются — в них тоже есть Name=,
    но это имена действий (Открыть новое окно, Quit Telegram и т.п.),
    а не приложения.
    Если ничего не нашли — app_id."""
    candidates = [
        os.path.expanduser(f'~/.local/share/flatpak/exports/share/applications/{app_id}.desktop'),
        f'/var/lib/flatpak/exports/share/applications/{app_id}.desktop',
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            name_ru = None
            name_default = None
            in_entry = False
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.rstrip('\n')
                    if line.startswith('['):
                        if line == '[Desktop Entry]':
                            in_entry = True
                            continue
                        if in_entry:
                            break
                        continue
                    if not in_entry:
                        continue
                    if line.startswith('Name[ru]='):
                        if name_ru is None:
                            name_ru = line[len('Name[ru]='):].strip()
                    elif line.startswith('Name='):
                        if name_default is None:
                            name_default = line[len('Name='):].strip()
            return name_ru or name_default or app_id
        except Exception:
            continue
    return app_id


def get_installed_apps():
    """Множество ID установленных Flatpak-приложений (system + user, дедуп)."""
    try:
        out = subprocess.check_output(
            ['flatpak', 'list', '--app', '--columns=application'],
            text=True, stderr=subprocess.DEVNULL,
        )
    except Exception:
        return set()
    apps = set()
    for line in out.split('\n'):
        line = line.strip()
        if line and '.' in line and not line.startswith('Application'):
            apps.add(line)
    return apps


def get_running_apps():
    """Множество ID запущенных Flatpak-приложений."""
    try:
        out = subprocess.check_output(
            ['flatpak', 'ps', '--columns=application'],
            text=True, stderr=subprocess.DEVNULL,
        )
    except Exception:
        return set()
    apps = set()
    for line in out.split('\n'):
        line = line.strip()
        if line and '.' in line and not line.startswith('Application'):
            apps.add(line)
    return apps


def du_sb(path):
    """Размер каталога в байтах (du -sb). 0, если не существует или ошибка."""
    if not os.path.exists(path):
        return 0
    try:
        out = subprocess.check_output(['du', '-sb', path], text=True, stderr=subprocess.DEVNULL)
        return int(out.split()[0])
    except Exception:
        return 0


def df_free(path):
    """Свободное место на разделе, где находится path, в байтах.
    Если path не существует — поднимается до первого существующего предка."""
    p = os.path.abspath(path)
    while p != '/' and not os.path.exists(p):
        p = os.path.dirname(p)
    try:
        out = subprocess.check_output(['df', '-P', p], text=True, stderr=subprocess.DEVNULL)
        lines = out.strip().split('\n')
        if len(lines) < 2:
            return 0
        parts = lines[1].split()
        if len(parts) < 4:
            return 0
        return int(parts[3]) * 1024
    except Exception:
        return 0


def _existing_ancestor(path):
    p = os.path.abspath(path)
    while p != '/' and not os.path.exists(p):
        p = os.path.dirname(p)
    return p or '/'


def same_fs(path_a, path_b):
    """True, если оба пути находятся на одной файловой системе."""
    try:
        return os.stat(_existing_ancestor(path_a)).st_dev == os.stat(_existing_ancestor(path_b)).st_dev
    except Exception:
        return True


def human_size(num_bytes):
    """Форматирование байтов в человекочитаемый вид: '1.5 ГБ', '350 МБ' и т.д."""
    num_bytes = float(num_bytes)
    if num_bytes < 1024:
        return f"{int(num_bytes)} Б"
    for unit in ('КБ', 'МБ', 'ГБ', 'ТБ'):
        num_bytes /= 1024.0
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
    return f"{num_bytes:.1f} ПБ"


def _parse_install_line(line):
    """Разбирает одну строку вида:
        flatpak install -y flathub <id> #<name>;<desc>
    Возвращает (app_id, name, desc) или (None, None, None) при несоответствии."""
    if '#' in line:
        idx = line.index('#')
        cmd_part = line[:idx].strip()
        comment_part = line[idx + 1:].strip()
    else:
        cmd_part = line.strip()
        comment_part = ''

    tokens = cmd_part.split()
    if len(tokens) < 5 or tokens[0] != 'flatpak' or tokens[1] != 'install':
        return None, None, None
    app_id = tokens[4]

    if not comment_part:
        return app_id, app_id, None

    if ';' in comment_part:
        name_part, desc_part = comment_part.split(';', 1)
        name = name_part.strip()
        desc = desc_part.strip() or None
    else:
        name = comment_part.strip()
        desc = None

    if not name:
        name = app_id
    return app_id, name, desc


def parse_install_script(path):
    """Парсит .sh-скрипт установки. Возвращает список словарей:
        {'category': str|None, 'app_id': str, 'name': str, 'desc': str|None}
    Категория назначается из ближайшей вышестоящей строки, начинающейся с #,
    и сохраняется для всех последующих приложений до следующей категории."""
    result = []
    current_category = None
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith('#!'):
                    continue
                if line.startswith('#'):
                    current_category = line.lstrip('#').strip() or None
                    continue
                if line.startswith('flatpak install'):
                    app_id, name, desc = _parse_install_line(line)
                    if app_id:
                        result.append({
                            'category': current_category,
                            'app_id': app_id,
                            'name': name,
                            'desc': desc,
                        })
    except Exception:
        pass
    return result


def format_sizes(*values):
    """Форматирует произвольное число размеров в байтах в одной единице
    измерения (по наибольшему значению). Возвращает список строк."""
    if not values:
        return []
    max_val = max(values)
    if max_val >= 1024 ** 4:
        div, unit = 1024 ** 4, 'ТБ'
    elif max_val >= 1024 ** 3:
        div, unit = 1024 ** 3, 'ГБ'
    elif max_val >= 1024 ** 2:
        div, unit = 1024 ** 2, 'МБ'
    elif max_val >= 1024:
        div, unit = 1024, 'КБ'
    else:
        return [f"{int(v)} Б" for v in values]
    return [f"{v / div:.1f} {unit}" for v in values]
