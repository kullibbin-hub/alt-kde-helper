#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mДобавление пользователя в группы\033[0m"
echo -e "\033[1;36m========================================\033[0m"

USER="$USER"
echo -e "\033[1;33m→ Пользователь: $USER\033[0m"

echo -e "\033[1;33m→ Добавление в группу dialout...\033[0m"
sudo usermod -aG dialout "$USER"

echo -e "\033[1;33m→ Добавление в группу lp...\033[0m"
sudo usermod -aG lp "$USER"

echo -e "\033[1;33m→ Добавление в группу adbusers...\033[0m"
if getent group adbusers >/dev/null 2>&1; then
    sudo usermod -aG adbusers "$USER"
    echo -e "\033[1;32m✓ Группа adbusers добавлена\033[0m"
else
    echo -e "\033[1;33m⚠ Группа adbusers не существует, пропущено\033[0m"
fi

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Добавление групп завершено успешно\033[0m"
