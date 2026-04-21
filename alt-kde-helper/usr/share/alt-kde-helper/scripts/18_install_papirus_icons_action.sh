#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка цветных значков papirus\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
sudo apt-get update
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
    exit 1
fi

echo -e "\033[1;33m"
echo "========================================"
echo "  Установка может занимать несколько минут"
echo "  из-за большого количества маленьких файлов."
echo "  Наберитесь терпения..."
echo "========================================"
echo -e "\033[0m"
sleep 3

echo -e "\033[1;33m→ Установка papirus-remix-icon-theme...\033[0m"
sudo apt-get install -y papirus-remix-icon-theme
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось установить papirus-remix-icon-theme\033[0m"
    exit 1
fi

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Цветные значки papirus успешно установлены\033[0m"
