#!/bin/bash
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mВосстановление работы USB-принтера\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# 1. Обновление индексов
echo -e "\033[1;33m→ Обновление индексов репозиториев...\033[0m"
sudo apt-get update
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить индексы. Проверьте подключение к интернету.\033[0m"
    exit 1
fi

# 2. Удаление ipp-usb
echo -e "\033[1;33m→ Удаление пакета ipp-usb...\033[0m"
sudo apt-get remove -y ipp-usb
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось удалить ipp-usb. Возможно, apt-get занят другим процессом.\033[0m"
    exit 1
fi

# 3. Установка ipp-usb
echo -e "\033[1;33m→ Установка пакета ipp-usb...\033[0m"
sudo apt-get install -y ipp-usb
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось установить ipp-usb.\033[0m"
    exit 1
fi

# 4. Перезапуск udev и ipp-usb
echo -e "\033[1;33m→ Перезапуск udev и ipp-usb...\033[0m"
sudo udevadm control --reload
sudo udevadm trigger --action=add --subsystem-match=usb
sudo systemctl restart ipp-usb.service 2>/dev/null || true

echo -e "\033[1;32m✅ Пакет ipp-usb переустановлен. Если принтер не определился, переподключите USB-кабель.\033[0m"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"