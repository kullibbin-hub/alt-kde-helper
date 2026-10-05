#!/bin/bash
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mПодключение зеркала Flathub ALT Gnome\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Получаем GPG-ключ
curl -s https://flathub.alt-gnome.ru/repo/flathub.flatpakrepo \
| awk -F= '/^GPGKey/{print $2}' \
| base64 -d > /tmp/proxy.gpg

if [ $? -ne 0 ] || [ ! -s /tmp/proxy.gpg ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось получить GPG-ключ Flathub ALT Gnome\033[0m"
    exit 1
fi

# Меняем URL
sudo flatpak remote-modify --url=https://flathub.alt-gnome.ru/repo flathub
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось изменить адрес Flathub\033[0m"
    rm -f /tmp/proxy.gpg
    exit 1
fi

# Импортируем GPG-ключ
sudo flatpak remote-modify --gpg-import=/tmp/proxy.gpg flathub
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось импортировать GPG-ключ Flathub ALT Gnome\033[0m"
    rm -f /tmp/proxy.gpg
    exit 1
fi
rm -f /tmp/proxy.gpg

# Проверка доступности зеркала через flatpak
echo -e "\033[1;33m→ Проверка доступности зеркала ALT Gnome через flatpak...\033[0m"
if flatpak remote-ls flathub --system >/dev/null 2>&1; then
    echo -e "\033[1;32m✅ Зеркало ALT Gnome успешно подключено и доступно.\033[0m"
else
    echo -e "\033[1;31m⚠ Зеркало ALT Gnome недоступно!\033[0m"
    echo -e "\033[1;33m→ Автоматический возврат к стандартному зеркалу Flathub...\033[0m"

    sudo flatpak remote-modify --url=https://dl.flathub.org/repo flathub

    echo -e "\033[1;32m✅ Установлено стандартное зеркало (dl.flathub.org) в целях безопасности.\033[0m"
fi

# Удаляем себя из очереди действий
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
exit 0
