#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка пакетов по списку\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Определяем текущую версию программы
VERSION_FILE="/usr/share/doc/alt-kde-helper/version.txt"
if [ -f "$VERSION_FILE" ]; then
    VERSION=$(cat "$VERSION_FILE" | tr -d '\n')
else
    echo -e "\033[1;31m❌ Ошибка: не удалось определить версию программы\033[0m"
    exit 1
fi

PACKAGES_FILE="$HOME/.config/alt-kde-helper/user_packages_${VERSION}.txt"

if [ ! -f "$PACKAGES_FILE" ]; then
    echo -e "\033[1;31m❌ Ошибка: файл со списком пакетов не найден\033[0m"
    echo -e "\033[1;31m   $PACKAGES_FILE\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
sudo apt-get update

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
    exit 1
fi

# Собираем список пакетов из файла, пропуская пустые строки и комментарии
PACKAGES=""
while IFS= read -r line || [ -n "$line" ]; do
    # Удаляем всё после # (включая сам #)
    line="${line%%#*}"
    # Удаляем пробелы в начале и конце
    pkg=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    # Пропускаем пустые строки
    if [ -n "$pkg" ]; then
        PACKAGES="$PACKAGES $pkg"
    fi
done < "$PACKAGES_FILE"

if [ -z "$PACKAGES" ]; then
    echo -e "\033[1;33m⚠ Список пакетов пуст. Нечего устанавливать.\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

echo -e "\033[1;33m→ Установка пакетов: $PACKAGES\033[0m"
sudo apt-get install -y $PACKAGES

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось установить пакеты\033[0m"
    exit 1
fi

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Пакеты успешно установлены\033[0m"
