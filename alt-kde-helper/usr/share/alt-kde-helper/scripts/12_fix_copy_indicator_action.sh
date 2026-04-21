#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mИсправление индикатора копирования файлов\033[0m"
echo -e "\033[1;36m========================================\033[0m"

DIRTY_FILE="/etc/sysctl.d/90-dirty.conf"

DIRTY_BYTES=$((64 * 1024 * 1024))
DIRTY_BG_BYTES=$((16 * 1024 * 1024))

echo -e "\033[1;33m→ Запись настроек в $DIRTY_FILE...\033[0m"
sudo bash -c "cat > $DIRTY_FILE" <<EOF
vm.dirty_bytes = $DIRTY_BYTES
vm.dirty_background_bytes = $DIRTY_BG_BYTES
EOF

echo -e "\033[1;33m→ Применение настроек...\033[0m"
sudo sysctl -p "$DIRTY_FILE"

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Индикатор копирования исправлен\033[0m"
