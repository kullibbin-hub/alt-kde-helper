#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат: удаление stplr и компонентов\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Удаление пакетов stplr
echo -e "\033[1;33m→ Удаление пакетов stplr, stplr-repo-aides, plasma-discover-stplr...\033[0m"
sudo apt-get remove -y stplr stplr-repo-aides plasma-discover-stplr

echo -e "\033[1;32m✅ Пакеты stplr удалены\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат установки stplr завершён\033[0m"
