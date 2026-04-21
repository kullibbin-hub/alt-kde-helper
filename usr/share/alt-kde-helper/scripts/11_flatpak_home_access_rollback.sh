#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат: доступ для flatpak к домашнему каталогу\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Удаление доступа к домашнему каталогу...\033[0m"
flatpak override --user --nofilesystem=home

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
rm -f "$STATE_DIR/11_flatpak_home_access_action.sh"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат выполнен успешно\033[0m"
