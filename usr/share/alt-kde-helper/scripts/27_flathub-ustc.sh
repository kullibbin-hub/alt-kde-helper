#!/bin/bash
echo -e "\033[1;33m→ Подключение зеркала Flathub USTC...\033[0m"

# Меняем URL
sudo flatpak remote-modify --url=https://mirrors.ustc.edu.cn/flathub flathub
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось изменить адрес Flathub\033[0m"
    exit 1
fi

# Проверка доступности зеркала
echo -e "\033[1;33m→ Проверка доступности зеркала USTC...\033[0m"
if ! curl -s -f -I --max-time 10 "https://mirrors.ustc.edu.cn/flathub/summary" > /dev/null 2>&1; then
    echo -e "\033[1;31m⚠ Зеркало USTC недоступно!\033[0m"
    echo -e "\033[1;33m→ Автоматический возврат к стандартному зеркалу Flathub...\033[0m"

    sudo flatpak remote-modify --url=https://dl.flathub.org/repo flathub

    echo -e "\033[1;33m⚠ Установлено стандартное зеркало (dl.flathub.org) в целях безопасности.\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 1
fi

echo -e "\033[1;32m✓ Flathub переключён на зеркало USTC\033[0m"
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
exit 0
