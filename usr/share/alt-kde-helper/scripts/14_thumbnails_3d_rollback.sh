#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат: показ миниатюр для 3D-файлов\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Удаление freecad-thumbnailer...\033[0m"
sudo rm -f /usr/local/bin/freecad-thumbnailer

echo -e "\033[1;33m→ Удаление FreeCAD1.thumbnailer...\033[0m"
sudo rm -f /usr/share/thumbnailers/FreeCAD1.thumbnailer

echo -e "\033[1;33m→ Удаление f3d...\033[0m"
sudo epm remove f3d

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
rm -f "$STATE_DIR/14_thumbnails_3d_action.sh"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат выполнен успешно\033[0m"
