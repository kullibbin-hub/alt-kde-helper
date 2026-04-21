#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка / обновление eepm\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Проверка наличия пакетов
if ! rpm -q eepm epmgpi eepm-play-gui &>/dev/null; then
    echo -e "\033[1;33m→ Некоторые пакеты eepm отсутствуют. Установка...\033[0m"

    echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
    sudo apt-get update
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
        exit 1
    fi

    echo -e "\033[1;33m→ Установка eepm, epmgpi, eepm-play-gui...\033[0m"
    sudo apt-get install -y eepm epmgpi eepm-play-gui
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить пакеты eepm\033[0m"
        exit 1
    fi
else
    echo -e "\033[1;32m✓ Все пакеты eepm уже установлены\033[0m"
fi

echo -e "\033[1;33m→ Обновление eepm...\033[0m"
sudo epm upgrade "https://download.etersoft.ru/pub/Korinf/x86_64/ALTLinux/p11/eepm-*.noarch.rpm"

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить eepm\033[0m"
    exit 1
fi

# Обновление софта, установленного через epm play
echo -e "\033[1;33m→ Обновление софта, установленного через epm play...\033[0m"
sudo epm play --update all

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ eepm успешно установлен/обновлён\033[0m"
