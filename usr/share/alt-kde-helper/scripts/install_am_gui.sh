#!/bin/bash

C_RED='\033[1;31m'
C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RESET='\033[0m'

echo -e "${C_CYAN}========================================${C_RESET}"
echo -e "${C_CYAN}Установка AM-GUI${C_RESET}"
echo -e "${C_CYAN}========================================${C_RESET}"
echo ""

# 1. Проверка архитектуры
ARCH=$(uname -m)
if [[ "$ARCH" != "x86_64" && "$ARCH" != "amd64" ]]; then
    echo -e "${C_RED}❌ Ошибка: AM-GUI доступен только для архитектуры x86_64/amd64.${C_RESET}"
    echo -e "${C_RED}Ваша архитектура: $ARCH${C_RESET}"
    echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
    read -n1
    exit 1
fi

# 2. Проверка наличия
TARGET="$HOME/bin/am-gui.AppImage"
if [ -f "$TARGET" ]; then
    echo -e "${C_GREEN}✅ AM-GUI уже установлен в: $TARGET${C_RESET}"
    echo -e "${C_CYAN}Запуск AM-GUI...${C_RESET}"
    nohup "$TARGET" > /dev/null 2>&1 &
    sleep 1
    exit 0
fi

# 3. Создание папок
mkdir -p "$HOME/bin"
CACHE_DIR="$HOME/.cache/alt-kde-helper"
mkdir -p "$CACHE_DIR"

echo -e "${C_YELLOW}→ Поиск последней версии AM-GUI на GitHub...${C_RESET}"

# 4. Получение URL последней версии AM-GUI для x86_64
DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/Shikakiben/AM-GUI/releases/latest" | grep "browser_download_url" | grep "x86_64.AppImage" | cut -d '"' -f 4 | head -n 1)
if [ -z "$DOWNLOAD_URL" ]; then
    echo -e "${C_RED}❌ Не удалось найти ссылку на скачивание AM-GUI для x86_64.${C_RESET}"
    echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
    read -n1
    exit 1
fi

echo -e "${C_CYAN}Найдена версия: $DOWNLOAD_URL${C_RESET}"
echo -e "${C_YELLOW}→ Скачивание AM-GUI...${C_RESET}"

# 5. Скачивание во временный файл
TEMP_FILE="$CACHE_DIR/am-gui-download.AppImage"
wget -q --show-progress -O "$TEMP_FILE" "$DOWNLOAD_URL"
if [ $? -ne 0 ]; then
    echo -e "${C_RED}❌ Ошибка при скачивании AM-GUI.${C_RESET}"
    rm -f "$TEMP_FILE"
    echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
    read -n1
    exit 1
fi

# 6. Проверка размера файла (минимум 10 МБ для AppImage)
FILE_SIZE=$(stat -c%s "$TEMP_FILE" 2>/dev/null || echo 0)
if [ "$FILE_SIZE" -lt 10000000 ]; then
    echo -e "${C_RED}❌ Файл скачался не полностью (размер: $FILE_SIZE байт)${C_RESET}"
    rm -f "$TEMP_FILE"
    echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
    read -n1
    exit 1
fi

# 7. Проверка, что это действительно AppImage (ELF + AppImage signature)
FILE_TYPE=$(file -b "$TEMP_FILE" 2>/dev/null)
if ! echo "$FILE_TYPE" | grep -q "ELF"; then
    echo -e "${C_RED}❌ Скачанный файл не является исполняемым (ELF).${C_RESET}"
    echo -e "${C_RED}Возможно, сервер вернул HTML-страницу ошибки.${C_RESET}"
    rm -f "$TEMP_FILE"
    echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
    read -n1
    exit 1
fi

# 8. Делаем исполняемым
chmod +x "$TEMP_FILE"

# 9. Перемещаем в целевое место
echo -e "${C_YELLOW}→ Установка в $TARGET...${C_RESET}"
mv "$TEMP_FILE" "$TARGET"

echo ""
echo -e "${C_GREEN}✅ AM-GUI успешно установлен в: $TARGET${C_RESET}"
echo -e "${C_CYAN}Запуск AM-GUI для первоначальной настройки...${C_RESET}"

# 10. Запуск AM-GUI
setsid "$TARGET" > /dev/null 2>&1 &
sleep 3

echo -e "${C_GREEN}Готово! Окно установки будет закрыто.${C_RESET}"
exit 0
