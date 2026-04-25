#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка Flatpak и репозитория Flathub\033[0m"
echo -e "\033[1;36m========================================\033[0m"

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"

FLAG_FILE="$STATE_DIR/$(basename "$0")"

# Удаляем старый флаг
rm -f "$FLAG_FILE"

# Проверка, установлены ли пакеты flatpak
if ! rpm -q flatpak flatpak-repo-flathub firsttime-flatpak-mask-openh264 flatpak-kcm plasma-discover-flatpak &>/dev/null; then
    echo -e "\033[1;33m→ Пакеты flatpak не установлены, или установлены не все. Установка...\033[0m"

    echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
    sudo apt-get update
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
        exit 1
    fi

    echo -e "\033[1;33m→ Установка flatpak, flatpak-repo-flathub, firsttime-flatpak-mask-openh264, flatpak-kcm, plasma-discover-flatpak...\033[0m"
    sudo apt-get install -y flatpak flatpak-repo-flathub firsttime-flatpak-mask-openh264 flatpak-kcm plasma-discover-flatpak
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить пакеты flatpak\033[0m"
        exit 1
    fi

    echo -e "\033[1;32m✅ Пакеты flatpak успешно установлены\033[0m"
else
    echo -e "\033[1;33m→ Пакеты flatpak уже установлены\033[0m"
fi

# Обновляем метаданные репозитория Flathub
echo -e "\033[1;33m→ Обновление метаданных Flathub...\033[0m"
flatpak update --appstream -y 2>/dev/null || true
echo -e "\033[1;32m✓ Метаданные Flathub обновлены\033[0m"

# Создаём флаг успешной установки
touch "$FLAG_FILE"
echo -e "\033[1;32m✓ Флаг установки создан\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Установка flatpak завершена\033[0m"
