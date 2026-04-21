#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mДоступ для flatpak ко всему домашнему каталогу на чтение\033[0m"
echo -e "\033[1;36m========================================\033[0m"

if ! command -v flatpak &> /dev/null; then
    echo -e "\033[1;33m→ flatpak не установлен. Установка...\033[0m"

    echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
    sudo apt-get update
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
        exit 1
    fi

    echo -e "\033[1;33m→ Установка flatpak и сопутствующих пакетов...\033[0m"
    sudo apt-get install -y flatpak flatpak-repo-flathub firsttime-flatpak-mask-openh264 flatpak-kcm plasma-discover-flatpak
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить flatpak\033[0m"
        exit 1
    fi
else
    echo -e "\033[1;32m✓ flatpak уже установлен\033[0m"
fi

echo -e "\033[1;33m→ Предоставление доступа на чтение к домашнему каталогу...\033[0m"
flatpak override --user --filesystem=home:ro

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Доступ для flatpak предоставлен\033[0m"
