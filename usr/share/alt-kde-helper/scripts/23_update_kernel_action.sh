#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОбновление ядра и модулей\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Запрос подтверждения через kdialog
kdialog --title "Обновление ядра" \
        --yesno "Внимание! Сейчас будет выполнено обновление ядра.\n\nВнимательно следите за выводом в терминале. Если появятся сообщения о нехватке модулей или ошибках — прервите выполнение (Ctrl+C или просто закройте терминал) и проконсультируйтесь с опытными пользователями.\n\nВ случае проблем при загрузке с новым ядром — всегда можно выбрать предыдущее ядро в меню загрузчика (Grub) при включении компьютера.\n\nПродолжить обновление?"
if [ $? -ne 0 ]; then
    echo -e "\033[1;33m⚠ Обновление ядра отменено пользователем\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

echo -e "\033[1;33m→ Обновление списков пакетов (apt)...\033[0m"
sudo apt-get update
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить списки пакетов\033[0m"
    exit 1
fi

# Находим последний доступный flavour ядра
LATEST_KERNEL=$(apt-cache search '^kernel-image-' | \
    grep -oP '^kernel-image-\K[0-9]+\.[0-9]+' | \
    sort -V | \
    tail -1)

if [ -z "$LATEST_KERNEL" ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось определить последнюю версию ядра\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Последний доступный flavour ядра: $LATEST_KERNEL\033[0m"

# Запускаем update-kernel с найденным flavour
sudo update-kernel -t "$LATEST_KERNEL"
UPDATE_OUTPUT=$(sudo update-kernel -t "$LATEST_KERNEL" 2>&1)
EXIT_CODE=$?

echo "$UPDATE_OUTPUT"

if [ $EXIT_CODE -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка при обновлении ядра\033[0m"
    kdialog --title "Обновление ядра" \
            --error "Произошла ошибка при обновлении ядра.\n\nПодробности смотрите в терминале."
    exit 1
fi

if echo "$UPDATE_OUTPUT" | grep -q "Everything is already installed"; then
    echo -e "\033[1;33m⚠
    Новых версий ядра нет
    \033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

echo -e "\033[1;32m✅ Обновление ядра и модулей завершено\033[0m"
kdialog --title "Обновление ядра" \
        --msgbox "Обновление ядра завершено.\n\nДля применения нового ядра требуется перезагрузка."
echo -e "\033[1;33m→ Для применения нового ядра требуется перезагрузка\033[0m"
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

