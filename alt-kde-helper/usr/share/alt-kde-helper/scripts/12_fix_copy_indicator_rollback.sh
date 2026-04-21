#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат: исправление индикатора копирования\033[0m"
echo -e "\033[1;36m========================================\033[0m"

DIRTY_FILE="/etc/sysctl.d/90-dirty.conf"

echo -e "\033[1;33m→ Удаление файла $DIRTY_FILE...\033[0m"
sudo rm -f "$DIRTY_FILE"

echo -e "\033[1;33m→ Перечитывание настроек по умолчанию...\033[0m"
sudo sysctl -p

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
rm -f "$STATE_DIR/12_fix_copy_indicator_action.sh"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат выполнен успешно\033[0m"
