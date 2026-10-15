#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУдаление действий из контекстного меню Dolphin\033[0m"
echo -e "\033[1;36m========================================\033[0m"

SERVICEMENUS_DIR="$HOME/.local/share/kio/servicemenus"
DESKTOP_FILE="$SERVICEMENUS_DIR/alt-kde-helper-actions.desktop"

# Удаляем файл действия
if [ -f "$DESKTOP_FILE" ]; then
    echo -e "\033[1;33m→ Удаление файла действий...\033[0m"
    rm -f "$DESKTOP_FILE"
    echo -e "\033[1;32m✓ Удалён файл: $DESKTOP_FILE\033[0m"
else
    echo -e "\033[1;33m→ Файл не найден: $DESKTOP_FILE\033[0m"
fi

# Удаляем каталог, только если он пуст
if [ -d "$SERVICEMENUS_DIR" ]; then
    if rmdir "$SERVICEMENUS_DIR" 2>/dev/null; then
        echo -e "\033[1;32m✓ Удалён пустой каталог: $SERVICEMENUS_DIR\033[0m"
    else
        echo -e "\033[1;33m→ Каталог не пуст, оставлен: $SERVICEMENUS_DIR\033[0m"
    fi
fi

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Действия для Dolphin удалены\033[0m"
