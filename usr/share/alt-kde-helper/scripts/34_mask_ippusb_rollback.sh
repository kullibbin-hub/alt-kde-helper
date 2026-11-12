#!/bin/bash
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mВключение ipp-usb (снятие маскировки)\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Снятие маскировки с ipp-usb...\033[0m"
sudo systemctl unmask ipp-usb

echo -e "\033[1;33m→ Запуск службы ipp-usb...\033[0m"
sudo systemctl start ipp-usb

echo -e "\033[1;32m✅ Служба ipp-usb снята с маскировки и запущена.\033[0m"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"