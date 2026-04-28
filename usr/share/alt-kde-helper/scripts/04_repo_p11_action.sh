#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка репозитория по умолчанию\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Определяем версию дистрибутива
RELEASE_FILE="/etc/altlinux-release"
if [ ! -f "$RELEASE_FILE" ]; then
    echo -e "\033[1;31m❌ Ошибка: не найден файл $RELEASE_FILE\033[0m"
    exit 1
fi

RELEASE_INFO=$(cat "$RELEASE_FILE")
echo -e "\033[1;33m→ Обнаружена система: $RELEASE_INFO\033[0m"

# Выбираем репозиторий в зависимости от версии
if echo "$RELEASE_INFO" | grep -qi "Sisyphus"; then
    REPO="sisyphus"
elif echo "$RELEASE_INFO" | grep -qi "p11"; then
    REPO="p11"
elif echo "$RELEASE_INFO" | grep -qi "p12"; then
    REPO="p12"
else
    echo -e "\033[1;31m❌ Ошибка: не удалось определить версию дистрибутива\033[0m"
    echo -e "\033[1;33m→ Найдено: $RELEASE_INFO\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Установка репозитория $REPO...\033[0m"
sudo apt-repo set "$REPO"

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"

# Создаём флаг текущего скрипта (имя не меняем для обратной совместимости)
touch "$STATE_DIR/04_repo_p11_action.sh"

# Удаляем флаги других зеркал
rm -f "$STATE_DIR/02_repo_fast_mirror_action.sh"
rm -f "$STATE_DIR/03_repo_yandex_action.sh"

echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
sudo apt-get update

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Репозиторий $REPO успешно установлен\033[0m"
