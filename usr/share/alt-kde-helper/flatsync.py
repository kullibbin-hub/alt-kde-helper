# flatsync.py - синхронизация flatinstall.sh с GitHub

import os
import urllib.request

RAW_URL = "https://raw.githubusercontent.com/kullibbin-hub/alt-kde-helper/main/flatinstall.sh"
TIMEOUT = 10
MIN_SIZE = 100
USER_AGENT = "Alt-KDE-Helper/FlatSync"

def _http_get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def _read_bytes(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

def _atomic_write_bytes(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)

def _is_valid_bash_script(data):
    """Проверяет, что данные — это bash-скрипт, а не HTML-ошибка."""
    try:
        text = data[:200].decode('utf-8', errors='ignore').strip()
        if not text.startswith('#!'):
            return False
        first_line = text.split('\n')[0]
        if 'bash' not in first_line and 'sh' not in first_line:
            return False
        if '<html' in text.lower() or '<!doctype' in text.lower():
            return False
        return True
    except Exception:
        return False

def _read_marker(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""

def _write_marker(path, version):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(version)
    except Exception:
        pass

def do_sync(version, on_state, scripts_path, home_path, marker_path):
    """Синхронизация flatinstall.sh.
    1. Если программа обновилась (маркер != version) — копирует из scripts_path в home_path.
    2. on_state('checking'), скачивает RAW_URL с таймаутом 10 с.
    3. Совпадает с home_path → on_state('unchanged').
       Отличается → атомарная запись → on_state('updated').
       HTTP-ошибка → on_state('failed').
    """
    # Шаг 1: восстановление после обновления программы
    if _read_marker(marker_path) != version:
        src = _read_bytes(scripts_path)
        if src is not None:
            try:
                _atomic_write_bytes(home_path, src)
                _write_marker(marker_path, version)
            except Exception:
                pass

    # Шаг 2: скачивание
    on_state('checking')
    try:
        data = _http_get(RAW_URL)
    except Exception:
        on_state('failed')
        return

    if len(data) < MIN_SIZE or not _is_valid_bash_script(data):
        on_state('failed')
        return

    # Шаг 3: сравнение и запись
    if _read_bytes(home_path) == data:
        on_state('unchanged')
        return

    try:
        _atomic_write_bytes(home_path, data)
    except Exception:
        on_state('failed')
        return

    on_state('updated')
