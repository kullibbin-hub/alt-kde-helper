#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат: удаление Flatpak и компонентов\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Предупреждение через kdialog
kdialog --title "Удаление Flatpak" \
        --warningcontinuecancel "Внимание! После удаления Flatpak все установленные Flatpak-приложения перестанут работать и будут удалены.\n\nПродолжить?"

if [ $? -ne 0 ]; then
    # Пользователь отказался - удаляем себя из очереди
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    echo -e "\033[1;33m⚠ Откат установки Flatpak отменён пользователем\033[0m"
    exit 0
fi

# Удаляем все Flatpak-приложения
echo -e "\033[1;33m→ Удаление всех Flatpak-приложений...\033[0m"
flatpak uninstall --all -y 2>/dev/null || true

# Удаляем пакеты flatpak
echo -e "\033[1;33m→ Удаление пакетов flatpak, flatpak-repo-flathub, firsttime-flatpak-mask-openh264, flatpak-kcm, plasma-discover-flatpak...\033[0m"
sudo apt-get remove -y flatpak flatpak-repo-flathub firsttime-flatpak-mask-openh264 flatpak-kcm plasma-discover-flatpak

echo -e "\033[1;32m✅ Пакеты flatpak удалены\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат установки flatpak завершён\033[0m"
