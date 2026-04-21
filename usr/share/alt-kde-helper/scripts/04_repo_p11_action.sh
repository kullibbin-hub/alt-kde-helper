#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка репозитория по умолчанию (p11)\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Установка репозитория p11...\033[0m"
sudo apt-repo set p11

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"

# Создаём флаг текущего скрипта
touch "$STATE_DIR/04_repo_p11_action.sh"

# Удаляем флаги других зеркал
rm -f "$STATE_DIR/02_repo_fast_mirror_action.sh"
rm -f "$STATE_DIR/03_repo_yandex_action.sh"

echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
sudo apt-get update

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Репозиторий p11 успешно установлен\033[0m"
