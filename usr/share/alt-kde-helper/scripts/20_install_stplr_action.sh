#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка stplr и репозитория aides\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
sudo apt-get update
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Установка stplr, stplr-repo-aides, plasma-discover-stplr...\033[0m"
sudo apt-get install -y stplr stplr-repo-aides plasma-discover-stplr
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось установить пакеты\033[0m"
    exit 1
fi

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ stplr и репозиторий aides успешно установлены\033[0m"
