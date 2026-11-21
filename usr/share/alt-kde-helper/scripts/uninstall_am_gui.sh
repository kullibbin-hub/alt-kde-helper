#!/bin/bash
C_RED='\033[1;31m'
C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RESET='\033[0m'

echo -e "${C_CYAN}========================================${C_RESET}"
echo -e "${C_CYAN}Удаление AM-GUI${C_RESET}"
echo -e "${C_CYAN}========================================${C_RESET}"
echo ""

# 1. Удаление исполняемого файла (исправлен путь на ~/bin)
TARGET="$HOME/bin/am-gui.AppImage"
if [ -f "$TARGET" ]; then
    echo -e "${C_YELLOW}→ Удаление $TARGET...${C_RESET}"
    rm -f "$TARGET"
    echo -e "${C_GREEN}✅ Исполняемый файл удалён.${C_RESET}"
else
    echo -e "${C_YELLOW}⚠️ Файл $TARGET не найден.${C_RESET}"
fi

# Также проверим старый путь на всякий случай
if [ -f "$HOME/.local/bin/am-gui" ]; then
    rm -f "$HOME/.local/bin/am-gui"
fi

# Проверим вариант с расширением
if [ -f "$HOME/.local/bin/am-gui.AppImage" ]; then
    rm -f "$HOME/.local/bin/am-gui.AppImage"
fi

# Удаление симлинка appman из ~/bin и самого appman из ~/.local/bin
rm -f "$HOME/bin/appman"
rm -f "$HOME/.local/bin/appman"

# 2. Удаление .desktop файлов
echo -e "${C_YELLOW}→ Удаление ярлыков из меню...${C_RESET}"
rm -f "$HOME/.local/share/applications/am-gui.desktop"
rm -f "$HOME/.local/share/applications/AM-GUI.desktop"
rm -f "$HOME/.local/share/applications/am-install.desktop"
rm -f "/usr/share/applications/am-gui.desktop"
rm -f "/usr/share/applications/AM-GUI.desktop"

# 3. Удаление иконок
echo -e "${C_YELLOW}→ Удаление иконок...${C_RESET}"
find "$HOME/.local/share/icons" -iname "*am-gui*" -type f -delete 2>/dev/null
find "$HOME/.local/share/icons" -iname "*am_gui*" -type f -delete 2>/dev/null

# 4. Удаление mime-типов
echo -e "${C_YELLOW}→ Удаление mime-типов...${C_RESET}"
rm -f "$HOME/.local/share/mime/packages/am-gui.xml"
rm -f "$HOME/.local/share/mime/packages/AM-GUI.xml"

# 5. Очистка кэша (добавлено)
echo -e "${C_YELLOW}→ Очистка кэша...${C_RESET}"
rm -rf "$HOME/.cache/alt-kde-helper/am-gui*" 2>/dev/null

# 6. Обновление кэша системы
echo -e "${C_YELLOW}→ Обновление кэша системы...${C_RESET}"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null
update-mime-database "$HOME/.local/share/mime" 2>/dev/null

echo ""
echo -e "${C_GREEN}✅ AM-GUI полностью удалён.${C_RESET}"
echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
read -n1
exit 0
