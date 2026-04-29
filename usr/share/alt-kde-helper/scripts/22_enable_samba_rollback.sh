#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОтключение локальной сети (Samba)\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Остановка и отключение сервисов smb и nmb...\033[0m"
sudo systemctl disable --now smb nmb 2>/dev/null

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Сервисы Samba остановлены и отключены\033[0m"
