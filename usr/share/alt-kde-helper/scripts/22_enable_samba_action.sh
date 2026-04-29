#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mВключение локальной сети (Samba)\033[0m"
echo -e "\033[1;36m========================================\033[0m"

if ! rpm -q samba samba-client &>/dev/null; then
    echo -e "\033[1;31m❌ Ошибка: пакеты samba и/или samba-client не установлены\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Включение и запуск сервисов smb и nmb...\033[0m"
sudo systemctl enable --now smb nmb

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось включить сервисы Samba\033[0m"
    exit 1
fi

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Сервисы Samba включены и запущены\033[0m"
