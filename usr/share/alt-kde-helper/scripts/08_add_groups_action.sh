#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mДобавление пользователя в группы dialout, lp, adbusers\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Скрипт добавляет текущего пользователя в группы dialout, lp и adbusers (если группа существует)
# А также настраивает права доступа для программатора USBasp

# Получаем имя текущего пользователя
USER_NAME="$USER"

# Добавляем в группу dialout
echo -e "\033[1;33m→ Добавление пользователя $USER_NAME в группу dialout...\033[0m"
sudo usermod -aG dialout "$USER_NAME"

# Добавляем в группу lp
echo -e "\033[1;33m→ Добавление пользователя $USER_NAME в группу lp...\033[0m"
sudo usermod -aG lp "$USER_NAME"

# Добавляем в группу adbusers (если существует)
if getent group adbusers >/dev/null 2>&1; then
    echo -e "\033[1;33m→ Добавление пользователя $USER_NAME в группу adbusers...\033[0m"
    sudo usermod -aG adbusers "$USER_NAME"
else
    echo -e "\033[1;33m→ Группа adbusers не существует, пропускаем\033[0m"
fi

# ============================================================
# Настройка прав доступа для программатора USBasp
# ============================================================

UDEV_RULES_FILE="/etc/udev/rules.d/99-usbasp.rules"

# Проверяем, существует ли уже файл правил
if [ ! -f "$UDEV_RULES_FILE" ]; then
    echo -e "\033[1;33m→ Создание правил udev для USBasp...\033[0m"
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="16c0", ATTR{idProduct}=="05dc", MODE="0666", GROUP="dialout"' | sudo tee "$UDEV_RULES_FILE" > /dev/null
    echo -e "\033[1;32m✓ Правила для USBasp созданы: $UDEV_RULES_FILE\033[0m"

    # Перезагружаем правила udev
    echo -e "\033[1;33m→ Перезагрузка правил udev...\033[0m"
    sudo udevadm control --reload-rules && sudo udevadm trigger
    echo -e "\033[1;32m✓ Правила udev перезагружены\033[0m"
else
    echo -e "\033[1;33m→ Файл правил udev для USBasp уже существует, пропускаем\033[0m"
fi

echo -e "\033[1;32m✅ Пользователь $USER_NAME добавлен в необходимые группы\033[0m"
echo -e "\033[1;33m→ Для применения изменений групп выйдите из системы и зайдите снова\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
