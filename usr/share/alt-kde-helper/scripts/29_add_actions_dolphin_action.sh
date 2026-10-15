#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mДействия в контекстном меню Dolphin\033[0m"
echo -e "\033[1;36m========================================\033[0m"

SERVICEMENUS_DIR="$HOME/.local/share/kio/servicemenus"
DESKTOP_FILE="$SERVICEMENUS_DIR/alt-kde-helper-actions.desktop"

echo -e "\033[1;33m→ Определение редактора по умолчанию...\033[0m"

# Определяем редактор по умолчанию для текстовых файлов
EDITOR_CMD=""
EDITOR_ICON=""

DEFAULT_DESKTOP=$(xdg-mime query default text/plain 2>/dev/null)

if [ -n "$DEFAULT_DESKTOP" ]; then
    EDITOR_CMD=$(basename "$DEFAULT_DESKTOP" .desktop | sed 's/^org\.kde\.//')
    EDITOR_ICON="$EDITOR_CMD"
fi

# Fallback, если xdg-mime ничего не дал
if [ -z "$EDITOR_CMD" ]; then
    if command -v kwrite >/dev/null 2>&1; then
        EDITOR_CMD="kwrite"
        EDITOR_ICON="kwrite"
    elif command -v kate >/dev/null 2>&1; then
        EDITOR_CMD="kate"
        EDITOR_ICON="kate"
    fi
fi

# Создаём каталог, если его нет
mkdir -p "$SERVICEMENUS_DIR"

# Если редактор найден — создаём оба действия
if [ -n "$EDITOR_CMD" ]; then
    echo -e "\033[1;33m→ Создание файла с действиями (редактор: $EDITOR_CMD)...\033[0m"

    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Service
ServiceTypes=KonqPopupMenu/Plugin
MimeType=all/all;
Actions=openAsText;makeExecutable;
X-KDE-Priority=TopLevel

[Desktop Action openAsText]
Name=Open as text
Name[ru]=Открыть как текст
Icon=${EDITOR_ICON}
Exec=${EDITOR_CMD} %f

[Desktop Action makeExecutable]
Name=Make executable
Name[ru]=Сделать исполняемым
Icon=application-x-executable
Exec=chmod +x %f
EOF

    echo -e "\033[1;32m✓ Созданы действия:\033[0m"
    echo -e "  • Открыть как текст ($EDITOR_CMD)"
    echo -e "  • Сделать исполняемым"
else
    # Редактор не найден — создаём только «Сделать исполняемым»
    echo -e "\033[1;33m→ Редактор не найден, создание только «Сделать исполняемым»...\033[0m"

    cat > "$DESKTOP_FILE" << 'EOF'
[Desktop Entry]
Type=Service
ServiceTypes=KonqPopupMenu/Plugin
MimeType=all/all;
Actions=makeExecutable;
X-KDE-Priority=TopLevel

[Desktop Action makeExecutable]
Name=Make executable
Name[ru]=Сделать исполняемым
Icon=application-x-executable
Exec=chmod +x %f
EOF

    echo -e "\033[1;32m✓ Создано действие: Сделать исполняемым\033[0m"
fi

chmod +x "$DESKTOP_FILE"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Действия для Dolphin установлены\033[0m"
