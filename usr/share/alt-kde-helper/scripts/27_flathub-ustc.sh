#!/bin/bash
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mПодключение зеркала Flathub USTC\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Устанавливаем URL зеркала USTC
sudo flatpak remote-modify flathub --url=https://mirrors.ustc.edu.cn/flathub --system

echo -e "\033[1;33m→ Проверка доступности зеркала USTC через flatpak...\033[0m"

# Пытаемся получить список приложений с нового зеркала
# Если команда выполняется успешно (код возврата 0), зеркало работает
if flatpak remote-ls flathub --system >/dev/null 2>&1; then
    echo -e "\033[1;32m✅ Зеркало USTC успешно подключено и доступно.\033[0m"
else
    echo -e "\033[1;31m⚠ Зеркало USTC недоступно или не отвечает!\033[0m"
    echo -e "\033[1;33m→ Автоматический возврат к стандартному зеркалу Flathub...\033[0m"
    flatpak remote-modify flathub --url=https://dl.flathub.org/repo/ --system
    echo -e "\033[1;32m✅ Установлено стандартное зеркало (dl.flathub.org).\033[0m"
fi

# Удаляем себя из очереди действий
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
exit 0
