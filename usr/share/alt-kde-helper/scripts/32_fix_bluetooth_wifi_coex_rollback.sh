#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат исправления Wi-Fi и Bluetooth\033[0m"
echo -e "\033[1;36m========================================\033[0m"

CONFIG_FILE="/etc/modprobe.d/rtw88_core.conf"
REBOOT_FLAG="/tmp/alt-kde-helper-needs-reboot"

if [ -f "$CONFIG_FILE" ]; then
    echo -e "\033[1;33m→ Удаление конфига $CONFIG_FILE...\033[0m"
    sudo rm -f "$CONFIG_FILE"
    echo -e "\033[1;32m✓ Конфиг удалён\033[0m"
else
    echo -e "\033[1;33m→ Конфиг не найден: $CONFIG_FILE\033[0m"
fi

# Пересобираем initramfs
echo -e "\033[1;33m→ Пересборка initramfs...\033[0m"
sudo make-initrd -k "$(uname -r)"

echo -e "\033[1;33m⚠ Требуется перезагрузка для применения отката\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат выполнен. Перезагрузите компьютер.\033[0m"
