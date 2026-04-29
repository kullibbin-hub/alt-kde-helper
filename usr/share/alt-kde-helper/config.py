# config.py - конфигурация и стили Alt KDE Helper

import os

STYLESHEET = """
QMainWindow {
    background-color: palette(window);
}

/* Общий стиль для всех карточек */
QFrame[class="ActionCard"],
QFrame[class="SimpleActionCard"],
QFrame[class="MirrorCard"] {
    background-color: palette(base);
    border: 1px solid palette(mid);
    border-radius: 6px;
    margin-top: 2px;
    margin-bottom: 2px;
}

/* Карточка с выбранным действием (оранжевый фон) */
QFrame[class="ActionCardOrange"],
QFrame[class="SimpleActionCardOrange"] {
    background-color: #fff0e0;
    border: 1px solid #d35400;
    border-radius: 6px;
    margin-top: 2px;
    margin-bottom: 2px;
}

/* Карточка с применённым действием (зелёный фон) */
QFrame[class="ActionCardGreen"],
QFrame[class="SimpleActionCardGreen"] {
    background-color: #e8f5e9;
    border: 1px solid #2e7d32;
    border-radius: 6px;
    margin-top: 2px;
    margin-bottom: 2px;
}

/* Текст внутри карточек (без отдельного фона) */
QLabel[class="Description"],
QLabel[class="DescriptionOrange"],
QLabel[class="DescriptionGreen"] {
    font-weight: normal;
    padding: 4px;
    border-radius: 3px;
}

QLabel[class="DescriptionOrange"] {
    color: #d35400;
}

QLabel[class="DescriptionGreen"] {
    color: #2e7d32;
}

/* Кнопки внизу */
QPushButton[class="BottomButton"] {
    padding: 8px 16px;
    font-weight: bold;
    min-width: 120px;
}

/* Кнопки вкладок */
QPushButton[class="TabButton"] {
    text-align: center;
    padding: 8px 12px;
    margin-left: 5px;
    margin-right: 5px;
    font-weight: normal;
    border: none;
    border-radius: 4px;
    background-color: transparent;
    color: palette(text);
}
QPushButton[class="TabButton"]:hover {
    background-color: palette(alternate-base);
}
QPushButton[class="TabButtonActive"] {
    text-align: center;
    padding: 8px 12px;
    margin-left: 5px;
    margin-right: 5px;
    background-color: palette(highlight);
    color: palette(highlighted-text);
}
"""

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
