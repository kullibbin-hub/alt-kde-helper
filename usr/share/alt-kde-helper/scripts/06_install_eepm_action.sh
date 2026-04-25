#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка eepm\033[0m"
echo -e "\033[1;36m========================================\033[0m"

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"

FLAG_FILE="$STATE_DIR/$(basename "$0")"
UPDATE_SCRIPT="06_update_eepm_action.sh"
UPDATE_SCRIPT_PATH="/tmp/alt-kde-helper-actions/$UPDATE_SCRIPT"

# Абсолютный путь к папке со скриптами
SOURCE_SCRIPT_DIR="/opt/alt-kde-helper/usr/share/alt-kde-helper/scripts"

# Удаляем старый флаг
rm -f "$FLAG_FILE"

# Проверка, установлены ли пакеты eepm
if ! rpm -q eepm epmgpi eepm-play-gui &>/dev/null; then
    echo -e "\033[1;33m→ Пакеты eepm не установлены, или установлены не все. Установка...\033[0m"

    echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
    sudo apt-get update
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
        exit 1
    fi

    echo -e "\033[1;33m→ Установка eepm, epmgpi, eepm-play-gui...\033[0m"
    sudo apt-get install -y eepm epmgpi eepm-play-gui
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить пакеты eepm\033[0m"
        exit 1
    fi

    echo -e "\033[1;32m✅ Пакеты eepm успешно установлены\033[0m"
else
    echo -e "\033[1;33m→ Пакеты eepm уже установлены\033[0m"
fi

# Создаём флаг успешной установки
touch "$FLAG_FILE"
echo -e "\033[1;32m✓ Флаг установки создан\033[0m"

# Копируем скрипт обновления в очередь
if [ -f "$SOURCE_SCRIPT_DIR/$UPDATE_SCRIPT" ]; then
    cp "$SOURCE_SCRIPT_DIR/$UPDATE_SCRIPT" "$UPDATE_SCRIPT_PATH"
    echo -e "\033[1;33m→ Скрипт обновления добавлен в очередь\033[0m"
else
    echo -e "\033[1;31m❌ Ошибка: скрипт обновления не найден в $SOURCE_SCRIPT_DIR\033[0m"
    exit 1
fi

# Прямой вызов скрипта обновления
if [ -f "$UPDATE_SCRIPT_PATH" ]; then
    echo -e "\033[1;33m→ Запуск обновления eepm...\033[0m"
    bash "$UPDATE_SCRIPT_PATH"
fi

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Установка eepm завершена\033[0m"
