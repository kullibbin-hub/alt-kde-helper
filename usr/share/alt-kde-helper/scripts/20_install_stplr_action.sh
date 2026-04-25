#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка stplr и репозитория aides\033[0m"
echo -e "\033[1;36m========================================\033[0m"

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"

FLAG_FILE="$STATE_DIR/$(basename "$0")"

# Удаляем старый флаг
rm -f "$FLAG_FILE"

# Проверка, установлен ли пакет stplr-repo-aides
if ! rpm -q stplr stplr-repo-aides plasma-discover-stplr &>/dev/null; then
    echo -e "\033[1;33m→ Пакеты stplr не установлены, или установлены не все. Установка...\033[0m"

    echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
    sudo apt-get update
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
        exit 1
    fi

    echo -e "\033[1;33m→ Установка stplr, stplr-repo-aides, plasma-discover-stplr...\033[0m"
    sudo apt-get install -y stplr stplr-repo-aides plasma-discover-stplr
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить пакеты stplr\033[0m"
        exit 1
    fi

    echo -e "\033[1;32m✅ Пакеты stplr успешно установлены\033[0m"
else
    echo -e "\033[1;33m→ Пакет stplr-repo-aides уже установлен\033[0m"
fi

# Обновляем репозитории stplr
echo -e "\033[1;33m→ Обновление репозиториев stplr...\033[0m"
sudo stplr ref 2>/dev/null || true
echo -e "\033[1;32m✓ Репозитории stplr обновлены\033[0m"

# Создаём флаг успешной установки
touch "$FLAG_FILE"
echo -e "\033[1;32m✓ Флаг установки создан\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Установка stplr завершена\033[0m"
