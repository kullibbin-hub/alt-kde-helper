# flathubmeta.py - загрузка иконок и метаданных FlatHub с кэшированием
# Кэш (вечный, не удаляется при очистке):
# ~/.local/share/alt-kde-helper/flathub-icons/{app_id}.{png|svg}
# ~/.local/share/alt-kde-helper/flathub-meta/{app_id}.json
# Метаданные берутся из одного запроса к API FlatHub:
# https://flathub.org/api/v2/appstream/{app_id}
# Оттуда сразу: icon (URL картинки) и urls.homepage (сайт программы).
# Иконка скачивается по URL из ответа (не по угаданному пути).

import os
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtCore import QThread, pyqtSignal

API_URL_TEMPLATE = "https://flathub.org/api/v2/appstream/{app_id}"
TIMEOUT = 10
USER_AGENT = "Alt-KDE-Helper/FlathubMeta"
MIN_ICON_SIZE = 100  # байт, защита от пустых/битых ответов
MAX_WORKERS = 4

# ---------- пути к кэшу ----------

def get_cache_root():
    return os.path.expanduser('~/.local/share/alt-kde-helper')

def get_icons_dir():
    return os.path.join(get_cache_root(), 'flathub-icons')

def get_meta_dir():
    return os.path.join(get_cache_root(), 'flathub-meta')

def get_icon_path(app_id):
    return os.path.join(get_icons_dir(), f'{app_id}.png')

def get_meta_path(app_id):
    return os.path.join(get_meta_dir(), f'{app_id}.json')

# ---------- внутренние утилиты ----------

def _valid_app_id(app_id):
    """Защита от путей и мусора в app_id."""
    if not app_id or not isinstance(app_id, str):
        return False
    if '/' in app_id or '\\' in app_id:
        return False
    if app_id in ('.', '..'):
        return False
    return True

def _detect_image_type(data):
    """Определяет тип изображения по magic bytes. Возвращает 'png', 'svg' или None."""
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    try:
        text = data[:100].decode('utf-8', errors='ignore').strip()
        if text.startswith('<?xml') or text.startswith('<svg'):
            return 'svg'
    except Exception:
        pass
    return None

def _find_icon_path(app_id):
    """Ищет файл иконки с любым расширением. Возвращает путь или None."""
    base = get_icon_path(app_id).rsplit('.', 1)[0]
    for ext in ('.png', '.svg'):
        path = base + ext
        if os.path.isfile(path):
            return path
    return None

def _load_meta(app_id):
    """Читает JSON меты из кэша. None, если нет или битый."""
    path = get_meta_path(app_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None

def _save_meta(app_id, data):
    """Атомарная запись JSON меты."""
    path = get_meta_path(app_id)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        pass

def _download_icon(url, dest_base):
    """Скачивает иконку по URL, определяет тип, атомарно пишет в dest_base.{png|svg}.
    Возвращает путь к файлу или None при ошибке."""
    try:
        os.makedirs(os.path.dirname(dest_base), exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read()
        if len(data) < MIN_ICON_SIZE:
            return None
        img_type = _detect_image_type(data)
        if img_type is None:
            return None
        dest_path = f'{dest_base}.{img_type}'
        tmp = dest_path + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, dest_path)
        return dest_path
    except Exception:
        return None

# ---------- публичное API для GUI ----------

def get_cached_meta(app_id):
    """Возвращает (icon_path|None, homepage|None) из кэша.
    icon_path = None, если файла иконки нет на диске (тогда её надо докачать)."""
    if not _valid_app_id(app_id):
        return None, None
    meta = _load_meta(app_id)
    if meta is None:
        return None, None
    homepage = meta.get('homepage') or None
    icon_file = _find_icon_path(app_id)
    if icon_file:
        return icon_file, homepage
    return None, homepage

def fetch_and_cache(app_id):
    """Гарантирует, что мета и иконка в кэше. Возвращает (icon_path|'', homepage|None).
    Если скачать не удалось — icon_path = '' (иконка-заглушка ставится вызывающим),
    homepage = None (пункт «Сайт» будет серым)."""
    if not _valid_app_id(app_id):
        return '', None

    # Полный кэш — возвращаем сразу.
    icon_path, homepage = get_cached_meta(app_id)
    if icon_path:
        return icon_path, homepage

    # Мета есть, иконки нет — докачиваем только иконку по сохранённому icon_url.
    meta = _load_meta(app_id)
    if meta is not None:
        icon_url = meta.get('icon_url') or ''
        if icon_url:
            base = get_icon_path(app_id).rsplit('.', 1)[0]
            dest = _download_icon(icon_url, base)
            if dest:
                return dest, meta.get('homepage') or None
        return '', meta.get('homepage') or None

    # Кэша нет — идём в API.
    try:
        req = urllib.request.Request(
            API_URL_TEMPLATE.format(app_id=app_id),
            headers={'User-Agent': USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode('utf-8'))
    except Exception:
        return '', None

    icon_url = (data.get('icon') or '').strip()
    homepage = ((data.get('urls') or {}).get('homepage') or '').strip() or None

    icon_path = ''
    if icon_url:
        base = get_icon_path(app_id).rsplit('.', 1)[0]
        dest = _download_icon(icon_url, base)
        if dest:
            icon_path = dest

    # Мету пишем, только если есть хоть что-то полезное. Иначе при следующем
    # запуске попробуем снова (например, если API был временно недоступен).
    if icon_path or homepage:
        _save_meta(app_id, {
            'app_id': app_id,
            'icon_url': icon_url,
            'homepage': homepage,
        })

    return icon_path, homepage

# ---------- фоновый загрузчик ----------

class MetaWorker(QThread):
    """Качает мету и иконки в пул потоков. По каждому app_id эмитит
    meta_ready(app_id, icon_path, homepage).
    icon_path = '' — иконка недоступна (ставить заглушку).
    homepage = None — сайт не указан в FlatHub."""
    meta_ready = pyqtSignal(str, str, object)

    def __init__(self, app_ids, parent=None):
        super().__init__(parent)
        self.app_ids = [a for a in app_ids if _valid_app_id(a)]

    def run(self):
        if not self.app_ids:
            return
        workers = min(MAX_WORKERS, len(self.app_ids))
        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(fetch_and_cache, a): a for a in self.app_ids}
                for fut in as_completed(futures):
                    if self.isInterruptionRequested():
                        break
                    app_id = futures[fut]
                    try:
                        icon_path, homepage = fut.result()
                    except Exception:
                        icon_path, homepage = '', None
                    self.meta_ready.emit(app_id, icon_path or '', homepage)
        except Exception:
            # На случай непредвиденного сбоя пула — не роняем поток.
            pass
