#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mИсправление конфликта Wi-Fi и Bluetooth\033[0m"
echo -e "\033[1;36m========================================\033[0m"

CONFIG_FILE="/etc/modprobe.d/rtw88_core.conf"
REBOOT_FLAG="/tmp/alt-kde-helper-needs-reboot"

# Проверяем, что драйвер rtw88 загружен
if ! lsmod | grep -q "^rtw88_core"; then
    echo -e "\033[1;33m⚠ Драйвер rtw88_core не загружен.\033[0m"
    echo -e "\033[1;33m  Этот фикс предназначен для Wi-Fi/Bluetooth чипов Realtek RTL8821CE.\033[0m"
    echo -e "\033[1;33m  На вашей системе он не нужен.\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

echo -e "\033[1;33m→ Обнаружен драйвер rtw88_core\033[0m"

# Проверяем, не применён ли фикс уже
if [ -f "$CONFIG_FILE" ] && grep -q "disable_lps_deep=Y" "$CONFIG_FILE"; then
    echo -e "\033[1;32m✓ Фикс уже применён: $CONFIG_FILE\033[0m"
else
    echo -e "\033[1;33m→ Создание конфига $CONFIG_FILE...\033[0m"
    echo "options rtw88_core disable_lps_deep=Y" | sudo tee "$CONFIG_FILE" > /dev/null

    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось создать конфиг\033[0m"
        exit 1
    fi

    echo -e "\033[1;32m✓ Конфиг создан\033[0m"
fi

# Пересобираем initramfs
echo -e "\033[1;33m→ Пересборка initramfs...\033[0m"
sudo make-initrd -k "$(uname -r)"

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось пересобрать initramfs\033[0m"
    exit 1
fi

echo -e "\033[1;32m✓ initramfs пересобран\033[0m"

echo -e "\033[1;33m⚠ Требуется перезагрузка для применения фикса\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Фикс Wi-Fi/Bluetooth применён. Перезагрузите компьютер.\033[0m"
