#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mДоступ для flatpak ко всему домашнему каталогу на чтение\033[0m"
echo -e "\033[1;36m========================================\033[0m"

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
FLAG_FILE="$STATE_DIR/$(basename "$0")"

if command -v flatpak &> /dev/null; then
    echo -e "\033[1;32m✓ flatpak установлен\033[0m"

    echo -e "\033[1;33m→ Предоставление доступа на чтение к домашнему каталогу...\033[0m"
    flatpak override --user --filesystem=home:ro

    # Создаём флаг успешного выполнения
    touch "$FLAG_FILE"
    echo -e "\033[1;32m✓ Флаг установки создан\033[0m"
else
    echo -e "\033[1;33m⚠ flatpak не установлен. Доступ не предоставлен\033[0m"
    # Удаляем флаг, если он был
    rm -f "$FLAG_FILE"
fi

# Удаляем себя из очереди в любом случае
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Завершено\033[0m"
