#!/bin/bash

# 1. Если нет терминала — перезапускаем себя в Konsole
if [ -z "$KONSOLE_VERSION" ]; then
    konsole -e "$0" "$@"
    exit 0
fi

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

# 2. Основная логика удаления
PROG_NAME="alt-kde-helper"
INSTALL_DIR="/opt/$PROG_NAME"
REAL_HOME="$HOME"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}    Удаление Alt KDE Helper${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "${YELLOW}Пожалуйста, введите пароль администратора...${NC}"
echo

if pkexec bash -c "
    rm -f /usr/bin/$PROG_NAME
    rm -f /usr/share/applications/$PROG_NAME.desktop
    rm -rf $INSTALL_DIR
    rm -rf $REAL_HOME/.config/alt-kde-helper
    rm -rf /tmp/alt-kde-helper-actions
    rm -f /usr/share/icons/hicolor/scalable/apps/alt-kde-helper.svg
"; then
    echo -e "${GREEN}✓ Alt KDE Helper успешно удалён.${NC}"

    # Очистка кэша иконок и меню
    echo -e "${YELLOW}→ Очистка кэша иконок...${NC}"
    rm -f "$HOME/.cache/icon-cache.kcache" 2>/dev/null || true
    # Удаление пользовательских файлов и кэшей
    rm -f ~/.local/share/applications/alt-kde-helper.desktop
    rm -f ~/.local/share/kxmlgui5/alt-kde-helper 2>/dev/null
    rm -f ~/.cache/kmenuedit/* 2>/dev/null

# Обновление кэша меню
kbuildsycoca6 --noincremental 2>/dev/null || true

    echo -e "${YELLOW}→ Обновление кэша меню...${NC}"
    kbuildsycoca6 --noincremental 2>/dev/null || kbuildsycoca5 --noincremental 2>/dev/null || true

    echo -e "${GREEN}✓ Кэш обновлён.${NC}"
else
    echo -e "${RED}✗ Ошибка: удалить Alt KDE Helper не удалось.${NC}"
fi

echo
echo -e "${CYAN}Нажмите Enter для закрытия окна...${NC}"
read -n 1 -s
