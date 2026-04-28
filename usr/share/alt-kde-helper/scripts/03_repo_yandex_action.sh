#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mСмена зеркала на Яндексовское\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Проверка наличия eepm...\033[0m"

if ! command -v epm &> /dev/null; then
    echo -e "\033[1;33m→ eepm не установлен. Установка...\033[0m"
    sudo apt-get update
    sudo apt-get install -y eepm
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить eepm\033[0m"
        echo -e "\033[1;33m→ Зеркало Yandex не установлено, оставляем текущее зеркало\033[0m"
        rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
        exit 0
    fi
else
    echo -e "\033[1;32m✓ eepm уже установлен\033[0m"
fi

echo -e "\033[1;33m→ Смена зеркала на Яндекс...\033[0m"
sudo epm repo change yandex

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось сменить зеркало на Yandex\033[0m"
    echo -e "\033[1;33m→ Возвращаем стандартное зеркало\033[0m"
    bash "$(dirname "$0")/04_repo_p11_action.sh"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"

echo -e "\033[1;33m→ Обновление списка пакетов для проверки зеркала...\033[0m"
sudo apt-get update

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: зеркало Yandex не работает или проблемы с соединением\033[0m"
    echo -e "\033[1;33m→ Возвращаем стандартное зеркало p11\033[0m"
    bash "$(dirname "$0")/04_repo_p11_action.sh"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

# Всё успешно — создаём флаг
touch "$STATE_DIR/03_repo_yandex_action.sh"

# Удаляем флаги других зеркал
rm -f "$STATE_DIR/02_repo_fast_mirror_action.sh"
rm -f "$STATE_DIR/04_repo_p11_action.sh"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Зеркало успешно изменено на Яндексовское и проверено\033[0m"
