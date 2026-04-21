#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат: показ миниатюр для файлов .dwg\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Удаление симлинка nconvert...\033[0m"
sudo rm -f /usr/local/bin/nconvert

echo -e "\033[1;33m→ Удаление NConvert...\033[0m"
sudo rm -rf /usr/local/NConvert

echo -e "\033[1;33m→ Удаление dwg-thumbnail.sh...\033[0m"
sudo rm -f /usr/local/bin/dwg-thumbnail.sh

echo -e "\033[1;33m→ Удаление dwg.thumbnailer...\033[0m"
sudo rm -f /usr/share/thumbnailers/dwg.thumbnailer

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
rm -f "$STATE_DIR/15_thumbnails_dwg_action.sh"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат выполнен успешно\033[0m"
