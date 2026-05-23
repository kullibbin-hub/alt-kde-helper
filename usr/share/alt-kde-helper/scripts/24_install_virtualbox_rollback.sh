#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУдаление VirtualBox\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Остановка сервиса
echo -e "\033[1;33m→ Остановка сервиса VirtualBox...\033[0m"
sudo systemctl stop virtualbox.service 2>/dev/null
sudo systemctl disable virtualbox.service 2>/dev/null

# Выгрузка модулей ядра
echo -e "\033[1;33m→ Выгрузка модулей ядра...\033[0m"
sudo modprobe -r vboxdrv vboxnetadp vboxnetflt vboxpci 2>/dev/null

# Удаление VirtualBox через epm
echo -e "\033[1;33m→ Удаление VirtualBox...\033[0m"
epm remove virtualbox 2>/dev/null || sudo apt-get remove -y virtualbox

# Удаление модулей ядра, если остались
echo -e "\033[1;33m→ Удаление модулей ядра...\033[0m"
sudo rpm -e $(rpm -qa | grep "kernel-modules-virtualbox") 2>/dev/null

# Удаление чёрного списка KVM
if [ -f /etc/modprobe.d/blacklist-kvm-for-virtualbox.conf ]; then
    echo -e "\033[1;33m→ Удаление чёрного списка KVM...\033[0m"
    sudo rm -f /etc/modprobe.d/blacklist-kvm-for-virtualbox.conf
fi

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m========================================\033[0m"
echo -e "\033[1;32m✅ Удаление VirtualBox завершено!\033[0m"
echo -e "\033[1;32m========================================\033[0m"
echo -e "\033[1;33m→ Для полной очистки рекомендуется перезагрузить систему.\033[0m"
