#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка кодека openh264 для Flatpak\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Проверка, установлен ли уже кодек
if flatpak list | grep -q "org.freedesktop.Platform.openh264"; then
    # Кодек уже есть - просто создаём флаг и удаляем из очереди
    STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
    mkdir -p "$STATE_DIR"
    touch "$STATE_DIR/$(basename "$0")"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

# Кодека нет - показываем диалог
kdialog --title "Установка кодека openh264" \
        --warningcontinuecancel "Кодек openh264 устанавливается из стороннего источника.\n\nПродолжить?"

if [ $? -ne 0 ]; then
    # Пользователь отказался - удаляем из очереди (не ошибка), флаг не ставим
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    echo -e "\033[1;33m⚠ Установка кодека openh264 пропущена пользователем\033[0m"
    exit 0
fi

# Пользователь согласился - устанавливаем

# Проверяем, установлен ли stplr
if ! which stplr > /dev/null 2>&1; then
    echo -e "\033[1;33m→ Установка stplr...\033[0m"
    sudo apt-get update && sudo apt-get install -y stplr
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить stplr\033[0m"
        exit 1
    fi
else
    echo -e "\033[1;33m→ stplr уже установлен, пропускаем\033[0m"
fi

# Пытаемся установить из aides (с автоматическим выбором первого варианта)
echo -e "\033[1;33m→ Установка flatpak-fix-openh264...\033[0m"
printf "1\n" | yes | sudo stplr in aides/flatpak-fix-openh264 --pm-args "-y" 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "\033[1;33m→ Не удалось из aides, пробуем из test-flatpak-fix-openh264...\033[0m"

    # Добавляем репозиторий (если уже есть - ошибка игнорируется)
    sudo stplr repo add test-flatpak-fix-openh264 https://altlinux.space/aides-pkgs/flatpak-fix-openh264.git 2>/dev/null || true

    echo -e "\033[1;33m→ Обновление репозиториев stplr...\033[0m"
    sudo stplr ref
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось обновить репозитории stplr\033[0m"
        exit 1
    fi

    echo -e "\033[1;33m→ Установка flatpak-fix-openh264 из test-flatpak-fix-openh264...\033[0m"
    printf "1\n" | yes | sudo stplr in test-flatpak-fix-openh264/flatpak-fix-openh264 --pm-args "-y" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить flatpak-fix-openh264 ни из aides, ни из test-flatpak-fix-openh264\033[0m"
        exit 1
    fi
fi

# Успех - создаём флаг и удаляем из очереди
STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Кодек openh264 успешно установлен\033[0m"
