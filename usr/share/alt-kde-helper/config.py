# config.py - конфигурация и стили Alt KDE Helper

import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette

# Файл для сохранения настройки темы
def get_theme_config_path():
    """Возвращает путь к файлу с настройкой темы"""
    config_dir = os.path.expanduser('~/.config/alt-kde-helper')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'theme.conf')

def save_theme_setting(is_dark):
    """Сохраняет настройку темы (dark=true/false)"""
    with open(get_theme_config_path(), 'w') as f:
        f.write('dark=true\n' if is_dark else 'dark=false\n')

def load_theme_setting():
    """Загружает настройку темы, если файла нет — None (авто)"""
    try:
        with open(get_theme_config_path(), 'r') as f:
            content = f.read().strip()
            return 'dark=true' in content
    except:
        return None  # не задано — использовать системное определение

def is_dark_theme():
    """Определяет, используется ли тёмная тема оформления (авто)"""
    app = QApplication.instance()
    if not app:
        return False
    text_color = app.palette().color(QPalette.ColorRole.WindowText)
    bg_color = app.palette().color(QPalette.ColorRole.Window)
    return text_color.lightness() > bg_color.lightness()

def get_stylesheet(force_dark=None):
    """
    Возвращает стили в зависимости от темы.
    force_dark = True  -> тёмная тема
    force_dark = False -> светлая тема
    force_dark = None  -> автоопределение (по QPalette)
    """
    if force_dark is None:
        is_dark = is_dark_theme()
    else:
        is_dark = force_dark

    if is_dark:
        # Тёмная тема: тёмно-зелёный фон, светлый текст
        green_bg = "#1a4d1a"      # тёмно-зелёный фон карточки
        green_text = "#66ff66"     # ярко-зелёный текст
        orange_bg = "#4a2a1a"      # тёмно-оранжевый фон
        orange_text = "#ffa366"    # светло-оранжевый текст
    else:
        # Светлая тема: светлый фон, тёмный текст
        green_bg = "#e8f5e9"       # светло-зелёный фон карточки
        green_text = "#2e7d32"     # тёмно-зелёный текст
        orange_bg = "#fff0e0"      # светло-оранжевый фон
        orange_text = "#d35400"     # тёмно-оранжевый текст

    return f"""
QMainWindow {{
    background-color: palette(window);
}}

/* Общий стиль для всех карточек */
QFrame[class="ActionCard"],
QFrame[class="SimpleActionCard"],
QFrame[class="MirrorCard"] {{
    background-color: palette(base);
    border: 1px solid palette(mid);
    border-radius: 6px;
    margin-top: 2px;
    margin-bottom: 2px;
}}

/* Карточка с выбранным действием (оранжевый фон) */
QFrame[class="ActionCardOrange"],
QFrame[class="SimpleActionCardOrange"] {{
    background-color: {orange_bg};
    border: 1px solid {orange_text};
    border-radius: 6px;
    margin-top: 2px;
    margin-bottom: 2px;
}}

/* Карточка с применённым действием (зелёный фон) */
QFrame[class="ActionCardGreen"],
QFrame[class="SimpleActionCardGreen"] {{
    background-color: {green_bg};
    border: 1px solid {green_text};
    border-radius: 6px;
    margin-top: 2px;
    margin-bottom: 2px;
}}

/* Текст внутри карточек */
QLabel[class="DescriptionOrange"] {{
    color: {orange_text};
}}

QLabel[class="DescriptionGreen"] {{
    color: {green_text};
}}

/* Кнопки внизу */
QPushButton[class="BottomButton"] {{
    padding: 8px 16px;
    font-weight: bold;
    min-width: 120px;
}}

/* Кнопки вкладок */
QPushButton[class="TabButton"] {{
    text-align: center;
    padding: 8px 12px;
    margin-left: 5px;
    margin-right: 5px;
    font-weight: normal;
    border: none;
    border-radius: 4px;
    background-color: transparent;
    color: palette(text);
}}
QPushButton[class="TabButton"]:hover {{
    background-color: palette(alternate-base);
}}
QPushButton[class="TabButtonActive"] {{
    text-align: center;
    padding: 8px 12px;
    margin-left: 5px;
    margin-right: 5px;
    background-color: palette(highlight);
    color: palette(highlighted-text);
}}
"""

# Для обратной совместимости (если где-то используется STYLESHEET напрямую)
STYLESHEET = get_stylesheet()

def get_scripts_dir():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'scripts')

def get_state_dir():
    state_dir = os.path.expanduser('~/.config/alt-kde-helper/state.d')
    os.makedirs(state_dir, exist_ok=True)
    return state_dir

def get_actions_dir():
    actions_dir = '/tmp/alt-kde-helper-actions'
    os.makedirs(actions_dir, exist_ok=True)
    return actions_dir

def clear_actions_dir():
    actions_dir = get_actions_dir()
    for f in os.listdir(actions_dir):
        fpath = os.path.join(actions_dir, f)
        try:
            if os.path.isfile(fpath):
                os.unlink(fpath)
        except Exception:
            pass

def get_help_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'help.html')

def get_version():
    # Сначала пробуем найти в системе (установленный пакет)
    version_file = '/usr/share/doc/alt-kde-helper/version.txt'
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()

    # Если не нашли, пробуем в корне проекта (для разработки)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    version_file = os.path.join(base_dir, 'version.txt')
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return "unknown"
