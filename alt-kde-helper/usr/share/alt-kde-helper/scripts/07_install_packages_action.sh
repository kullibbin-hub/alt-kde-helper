#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка рекомендованных пакетов\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
sudo apt-get update

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Установка пакетов...\033[0m"
sudo apt-get install -y sudo synaptic-usermode epmgpi eepm-play-gui gearlever android-tools pipewire-jack git skanlite print-manager sane-airscan airsane gnome-disk-utility icon-theme-Papirus xdg-desktop-portal-gtk net-snmp kcm-grub2 kaccounts-providers avahi-daemon avahi-tools ffmpegthumbnailer mediainfo samba-usershares kdeconnect kamoso kio-admin stmpclean

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось установить пакеты\033[0m"
    exit 1
fi

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Рекомендованные пакеты успешно установлены\033[0m"
