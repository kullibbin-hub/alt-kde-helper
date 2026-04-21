#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mИсправление ошибки с прокси в Discover\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Остановка packagekit...\033[0m"
sudo systemctl stop packagekit

echo -e "\033[1;33m→ Удаление баз данных PackageKit...\033[0m"
sudo rm -rf /var/lib/PackageKit /var/cache/PackageKit

echo -e "\033[1;33m→ Запуск packagekit...\033[0m"
sudo systemctl start packagekit

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Discover успешно исправлен\033[0m"
