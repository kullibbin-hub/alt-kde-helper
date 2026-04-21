#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mВозврат шрифтов к исходному размеру\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Возврат шрифтов к стандартным значениям...\033[0m"

kwriteconfig6 --file kdeglobals --group General --key font "Noto Sans,9,-1,5,50,0,0,0,0,0"
kwriteconfig6 --file kdeglobals --group General --key fixed "Monospace,9,-1,5,50,0,0,0,0,0"
kwriteconfig6 --file kdeglobals --group General --key menuFont "Noto Sans,9,-1,5,50,0,0,0,0,0"
kwriteconfig6 --file kdeglobals --group General --key smallFont "Noto Sans,7,-1,5,50,0,0,0,0,0"
kwriteconfig6 --file kdeglobals --group WM --key activeFont "Noto Sans,9,-1,5,50,0,0,0,0,0"
kwriteconfig6 --file kdeglobals --group General --key toolBarFont "Noto Sans,9,-1,5,50,0,0,0,0,0"

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
rm -f "$STATE_DIR/13_increase_fonts_action.sh"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Шрифты возвращены к исходным значениям\033[0m"
echo -e "\033[1;33m⚠ Для полного применения может потребоваться перезапуск приложений.\033[0m"
