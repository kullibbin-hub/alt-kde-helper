#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОбновление AppImage через Gear Lever\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Определяем способ установки Gear Lever
GEARLEVER_CMD=""
if command -v gearlever >/dev/null 2>&1; then
    GEARLEVER_CMD="gearlever"
elif flatpak list 2>/dev/null | grep -q "it.mijorus.gearlever"; then
    GEARLEVER_CMD="flatpak run it.mijorus.gearlever"
fi

# Если Gear Lever не установлен — просто выходим без ошибки
if [ -z "$GEARLEVER_CMD" ]; then
    echo -e "\033[1;33m⚠ Gear Lever не установлен, пропуск\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

echo -e "\033[1;33m→ Обновление AppImage...\033[0m"
if ! $GEARLEVER_CMD --update --all -y; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить AppImage через Gear Lever\033[0m"
    exit 1
fi

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Обновление AppImage завершено\033[0m"
