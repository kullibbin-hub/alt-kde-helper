#!/bin/bash

C_RED='\033[1;31m'
C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RESET='\033[0m'

echo -e "${C_CYAN}========================================${C_RESET}"
echo -e "${C_CYAN}Установка иконок Papirus${C_RESET}"
echo -e "${C_CYAN}========================================${C_RESET}"
echo ""

echo -e "${C_YELLOW}→ Обновление списка пакетов...${C_RESET}"
sudo apt-get update
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${C_RED}❌ Не удалось установить иконки Papirus. Действие не будет применено.${C_RESET}"
    echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
    read -n1
    exit 1
fi

echo ""
echo -e "${C_YELLOW}→ Установка icon-theme-Papirus и icon-theme-Papirus-Dark...${C_RESET}"
sudo apt-get install -y icon-theme-Papirus icon-theme-Papirus-Dark
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${C_RED}❌ Не удалось установить иконки Papirus. Действие не будет применено.${C_RESET}"
    echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
    read -n1
    exit 1
fi

echo ""
echo -e "${C_GREEN}✅ Иконки Papirus успешно установлены.${C_RESET}"
echo -e "${C_YELLOW}Нажмите любую клавишу для выхода...${C_RESET}"
read -n1
exit 0