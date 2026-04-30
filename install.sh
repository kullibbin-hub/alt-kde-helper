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

# 2. Дальше — обычная логика установки
REAL_USER="${SUDO_USER:-$USER}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROG_NAME="alt-kde-helper"
INSTALL_DIR="/opt/$PROG_NAME"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}    Установка Alt KDE Helper${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "${YELLOW}Пожалуйста, введите пароль администратора...${NC}"
echo

# 3. Запуск pkexec с полной установкой
if pkexec bash -c "
    set -e

    # Флаг, нужно ли обновлять репозитории
    NEED_UPDATE=0

    # Проверка и установка sudo
    echo -e '\\033[1;33m→ Проверка зависимостей...\\033[0m'
    if ! command -v sudo &>/dev/null; then
        NEED_UPDATE=1
    fi

    # Проверка PyQt6
    if ! rpm -q python3-module-PyQt6 >/dev/null 2>&1; then
        NEED_UPDATE=1
    fi

    # Проверка 7-zip
    if ! rpm -q 7-zip >/dev/null 2>&1; then
        NEED_UPDATE=1
    fi

    # Если чего-то не хватает — обновляем репозитории
    if [ \$NEED_UPDATE -eq 1 ]; then
        echo -e '\\033[1;33m→ Обновление индексов репозиториев...\\033[0m'
        if ! apt-get update; then
            echo -e '\\033[1;31m❌ Ошибка: не удалось обновить репозитории\\033[0m'
            echo -e '\\033[1;33mПроверьте подключение к интернету\\033[0m'
            exit 1
        fi
        echo -e '\\033[1;32m✓ Репозитории обновлены\\033[0m'
    fi

    # Установка sudo (если нет)
    if ! command -v sudo &>/dev/null; then
        echo -e '\\033[1;33m→ Установка sudo...\\033[0m'
        if ! apt-get install -y sudo; then
            echo -e '\\033[1;31m❌ Критическая ошибка: не удалось установить sudo\\033[0m'
            echo -e '\\033[1;31mБез sudo программа не сможет работать. Установка прервана.\\033[0m'
            exit 1
        fi
        echo -e '\\033[1;32m✓ sudo установлен\\033[0m'
    else
        echo -e '\\033[1;32m✓ sudo уже установлен\\033[0m'
    fi

    # Установка PyQt6 (если нет)
    if ! rpm -q python3-module-PyQt6 >/dev/null 2>&1; then
        echo -e '\\033[1;33m→ Установка PyQt6...\\033[0m'
        if ! apt-get install -y python3-module-PyQt6; then
            echo -e '\\033[1;31m❌ Ошибка: не удалось установить PyQt6\\033[0m'
            echo -e '\\033[1;33mПроверьте подключение к интернету и репозитории\\033[0m'
            exit 1
        fi
        echo -e '\\033[1;32m✓ PyQt6 установлен\\033[0m'
    else
        echo -e '\\033[1;32m✓ PyQt6 уже установлен\\033[0m'
    fi

    # Установка 7-zip (если нет)
    if ! rpm -q 7-zip >/dev/null 2>&1; then
        echo -e '\\033[1;33m→ Установка 7-zip...\\033[0m'
        if ! apt-get install -y 7-zip; then
            echo -e '\\033[1;31m❌ Ошибка: не удалось установить 7-zip\\033[0m'
            echo -e '\\033[1;33mПрограмма будет работать, но для некоторых операций может потребоваться 7-zip\\033[0m'
        else
            echo -e '\\033[1;32m✓ 7-zip установлен\\033[0m'
        fi
    else
        echo -e '\\033[1;32m✓ 7-zip уже установлен\\033[0m'
    fi

    # Создаём каталоги
    mkdir -p $INSTALL_DIR/usr/share/$PROG_NAME
    mkdir -p $INSTALL_DIR/usr/share/applications

    # Копируем файлы
    cp -r '$SCRIPT_DIR/usr/share/$PROG_NAME'/* $INSTALL_DIR/usr/share/$PROG_NAME/
    cp '$SCRIPT_DIR/usr/share/applications/$PROG_NAME.desktop' $INSTALL_DIR/usr/share/applications/
    cp '$SCRIPT_DIR/$PROG_NAME' $INSTALL_DIR/
    cp '$SCRIPT_DIR/usr/share/alt-kde-helper/alt-kde-helper.svg' $INSTALL_DIR/usr/share/alt-kde-helper/
    cp '$SCRIPT_DIR/usr/share/alt-kde-helper/alt-kde-helper.svg' /usr/share/icons/hicolor/scalable/apps/

    # Копируем документацию и version.txt
    mkdir -p /usr/share/doc/$PROG_NAME
    cp '$SCRIPT_DIR/README.md' /usr/share/doc/$PROG_NAME/ 2>/dev/null || true
    cp '$SCRIPT_DIR/version.txt' /usr/share/doc/$PROG_NAME/
    cp '$SCRIPT_DIR/install.sh' /usr/share/doc/$PROG_NAME/
    cp '$SCRIPT_DIR/uninstall.sh' /usr/share/doc/$PROG_NAME/
    chmod 755 /usr/share/doc/$PROG_NAME/install.sh
    chmod 755 /usr/share/doc/$PROG_NAME/uninstall.sh

    # Права
    chmod +x $INSTALL_DIR/$PROG_NAME
    chmod 755 $INSTALL_DIR/usr/share/$PROG_NAME/scripts
    chmod +x $INSTALL_DIR/usr/share/$PROG_NAME/scripts/*.sh 2>/dev/null || true

    # Симлинк
    ln -sf $INSTALL_DIR/$PROG_NAME /usr/bin/$PROG_NAME

    # Desktop-файл в систему
    cp $INSTALL_DIR/usr/share/applications/$PROG_NAME.desktop /usr/share/applications/

    # Обновляем кэш меню от пользователя
    su -c 'kbuildsycoca6 --noincremental' '$REAL_USER' 2>/dev/null || \
    su -c 'kbuildsycoca5 --noincremental' '$REAL_USER' 2>/dev/null || true
"; then
    kbuildsycoca6 --noincremental
    echo -e "${GREEN}✓ Готово: Alt KDE Helper установлен.${NC}"

    # Очистка кэша иконок
    echo -e "${YELLOW}→ Очистка кэша иконок...${NC}"
    rm -f "$HOME/.cache/icon-cache.kcache" 2>/dev/null || true

    echo -e "${GREEN}✓ Кэш обновлён.${NC}"
else
    echo -e "${RED}✗ Ошибка: установка не выполнена.${NC}"
fi

echo
echo -e "${CYAN}Нажмите Enter для закрытия окна...${NC}"
read -n 1 -s
