#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОбновление системы\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Обновление списков пакетов (apt)...\033[0m"
sudo apt-get update
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить списки пакетов\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Установка обновлений (apt)...\033[0m"
sudo apt-get dist-upgrade -y
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось установить обновления\033[0m"
    exit 1
fi

# Обновление Flatpak (только если установлен, игнорируем ошибки)
if command -v flatpak &> /dev/null; then
    echo -e "\033[1;33m→ Обновление Flatpak-пакетов...\033[0m"
    flatpak update -y || true
fi

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Обновление системы завершено успешно\033[0m"
