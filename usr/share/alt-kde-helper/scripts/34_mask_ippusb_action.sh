#!/bin/bash
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОтключение ipp-usb (маскировка)\033[0m"
echo -e "\033[1;36m========================================\033[0m"

if ! rpm -q ipp-usb >/dev/null 2>&1; then
    echo -e "\033[1;33m⚠️  Пакет ipp-usb не установлен.\033[0m"
    echo -e "\033[1;33m   Перехватывать USB-принтер нечему, маскировка не требуется.\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

echo -e "\033[1;33m→ Остановка службы ipp-usb...\033[0m"
sudo systemctl stop ipp-usb 2>/dev/null || true

echo -e "\033[1;33m→ Маскировка службы ipp-usb...\033[0m"
sudo systemctl mask ipp-usb

echo -e "\033[1;32m✅ Служба ipp-usb остановлена и замаскирована.\033[0m"
echo -e "\033[1;32m   Принтер должен определиться в CUPS как USB-устройство.\033[0m"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"