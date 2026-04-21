#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mРемонт apt-get при ошибках\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Дедупликация apt-get...\033[0m"
sudo apt-get dedup
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось выполнить dedup\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Перестроение базы данных RPM...\033[0m"
sudo rpm --rebuilddb
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось перестроить базу RPM\033[0m"
    exit 1
fi

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Ремонт apt-get завершён успешно\033[0m"
