#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка кодека openh264 для Flatpak\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# 1. Проверка: установлен ли Flatpak
if ! rpm -q flatpak &>/dev/null; then
    echo -e "\033[1;31m❌ Ошибка: Flatpak не установлен\033[0m"
    echo -e "\033[1;33m→ Сначала установите Flatpak через программу\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

# 2. Проверка: установлен ли уже рантайм openh264
if flatpak list | grep -q "org.freedesktop.Platform.openh264"; then
    echo -e "\033[1;33m→ Кодек openh264 уже установлен\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

# 3. Предупреждение, что кодек из стороннего источника
kdialog --title "Установка кодека openh264" \
        --warningcontinuecancel "Кодек openh264 устанавливается из стороннего источника.\n\nПродолжить?"

if [ $? -ne 0 ]; then
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    echo -e "\033[1;33m⚠ Установка кодека openh264 пропущена пользователем\033[0m"
    exit 0
fi

# 4. Удаляем проблемный пакет (если есть)
sudo apt-get remove -y flatpak-fix-openh264+stplr-aides 2>/dev/null || true

# 5. Проверяем/устанавливаем stplr
if ! rpm -q stplr &>/dev/null; then
    echo -e "\033[1;33m→ Установка stplr...\033[0m"
    sudo apt-get update && sudo apt-get install -y stplr
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить stplr\033[0m"
        exit 1
    fi
else
    echo -e "\033[1;33m→ stplr уже установлен\033[0m"
fi

# 6. Проверяем/устанавливаем репозиторий aides
if ! rpm -q stplr-repo-aides &>/dev/null; then
    echo -e "\033[1;33m→ Установка репозитория aides...\033[0m"
    sudo apt-get install -y stplr-repo-aides
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить stplr-repo-aides\033[0m"
        exit 1
    fi
else
    echo -e "\033[1;33m→ Репозиторий aides уже установлен\033[0m"
fi

# 7. Обновляем индексы stplr
echo -e "\033[1;33m→ Обновление репозиториев stplr...\033[0m"
sudo stplr ref

# 8. Устанавливаем кодек
echo -e "\033[1;33m→ Установка flatpak-fix-openh264 из aides...\033[0m"
echo 1 | sudo stplr in aides/flatpak-fix-openh264 --pm-args "-y"

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось установить кодек openh264\033[0m"
    exit 1
fi

# 9. Успех
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Кодек openh264 для Flatpak успешно установлен\033[0m"
