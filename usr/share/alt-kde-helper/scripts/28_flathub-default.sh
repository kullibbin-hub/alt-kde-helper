#!/bin/bash

echo -e "\033[1;33m→ Восстановление стандартного зеркала Flathub...\033[0m"

sudo flatpak remote-modify --url=https://dl.flathub.org/repo flathub
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось восстановить стандартный адрес Flathub\033[0m"
    exit 1
fi

echo -e "\033[1;32m✓ Flathub переключён на стандартное зеркало\033[0m"
# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
exit 0
