#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mВключение 3D-ускорения для Google Chrome (Flatpak)\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Поиск Google Chrome в Flatpak...\033[0m"

if flatpak list --user --app 2>/dev/null | grep -q com.google.Chrome; then
    echo -e "\033[1;32m✓ Chrome найден в пользовательской установке flatpak\033[0m"
    flatpak override --user --socket=x11 --socket=wayland --device=dri com.google.Chrome
elif flatpak list --system --app 2>/dev/null | grep -q com.google.Chrome; then
    echo -e "\033[1;32m✓ Chrome найден в системной установке flatpak\033[0m"
    echo -e "\033[1;33m→ Используем пользовательские настройки (не требуют прав sudo)\033[0m"
    flatpak override --user --socket=x11 --socket=wayland --device=dri com.google.Chrome
else
    echo -e "\033[1;31m⚠ Google Chrome из Flatpak не установлен. Если он установлен из epm или stapler, ускорение включено по умолчанию.\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

# Проверяем результат
if [ $? -eq 0 ]; then
    STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
    mkdir -p "$STATE_DIR"
    touch "$STATE_DIR/$(basename "$0")"
    echo -e "\033[1;32m✅ 3D-ускорение для Google Chrome включено\033[0m"
else
    echo -e "\033[1;31m❌ Ошибка: не удалось включить 3D-ускорение\033[0m"
fi

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
