#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mРазрешение загрузки тем и виджетов из сети\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Включение GHNS в /etc/kf5/xdg/kdeglobals...\033[0m"
sudo sed -i 's/ghns=false/ghns=true/g' /etc/kf5/xdg/kdeglobals

echo -e "\033[1;33m→ Включение GHNS в /etc/xdg/kdeglobals...\033[0m"
sudo sed -i 's/ghns=false/ghns=true/g' /etc/xdg/kdeglobals

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Загрузка тем и виджетов из сети разрешена\033[0m"
