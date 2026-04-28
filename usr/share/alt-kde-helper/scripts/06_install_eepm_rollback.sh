#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат: удаление eepm\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Удаление пакетов eepm
echo -e "\033[1;33m→ Удаление пакетов eepm, epmgpi, eepm-play-gui...\033[0m"
sudo apt-get remove -y eepm epmgpi eepm-play-gui

echo -e "\033[1;32m✅ Пакеты eepm удалены\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат установки eepm завершён\033[0m"
