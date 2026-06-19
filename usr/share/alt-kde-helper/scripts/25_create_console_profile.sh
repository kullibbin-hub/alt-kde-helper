#!/bin/bash


echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mСоздание профиля Konsole \"Белый_текст\"\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Путь к папке профилей Konsole
KONSOLE_PROFILE_DIR="$HOME/.local/share/konsole"
PROFILE_NAME="Белый_текст"
PROFILE_FILE="$KONSOLE_PROFILE_DIR/$PROFILE_NAME.profile"
PROFILE_NAME_FOR_CONFIG="${PROFILE_NAME}.profile"

# Создаём папку, если её нет
mkdir -p "$KONSOLE_PROFILE_DIR"

# Проверяем, существует ли уже профиль
if [ -f "$PROFILE_FILE" ]; then
    echo -e "\033[1;33m→ Профиль \"$PROFILE_NAME\" уже существует. Пропускаем создание.\033[0m"
else
    echo -e "\033[1;33m→ Создание профиля \"$PROFILE_NAME\"...\033[0m"

    # Записываем содержимое профиля
    cat > "$PROFILE_FILE" << 'EOF'
[Appearance]
ColorScheme=Breeze

[General]
Name=Белый_текст
Parent=FALLBACK/
EOF

    echo -e "\033[1;32m✓ Профиль \"$PROFILE_NAME\" успешно создан.\033[0m"
fi

# ============================================================
# Устанавливаем созданный профиль как профиль по умолчанию
# ============================================================

KONSOLERC="$HOME/.config/konsolerc"

if [ ! -f "$KONSOLERC" ]; then
    # Если файла нет, создаём его с минимальным содержимым
    mkdir -p "$(dirname "$KONSOLERC")"
    echo "[Desktop Entry]" > "$KONSOLERC"
    echo "DefaultProfile=$PROFILE_NAME_FOR_CONFIG" >> "$KONSOLERC"
    echo -e "\033[1;32m✓ Файл konsolerc создан, профиль \"$PROFILE_NAME\" установлен как основной\033[0m"
else
    # Если файл есть, изменяем параметр DefaultProfile
    if grep -q "^DefaultProfile=" "$KONSOLERC"; then
        # Параметр существует — заменяем его
        sed -i "s/^DefaultProfile=.*/DefaultProfile=$PROFILE_NAME_FOR_CONFIG/" "$KONSOLERC"
        echo -e "\033[1;32m✓ Профиль \"$PROFILE_NAME\" установлен как основной\033[0m"
    else
        # Параметра нет — добавляем его в секцию [Desktop Entry]
        if grep -q "^\[Desktop Entry\]" "$KONSOLERC"; then
            # Секция есть — добавляем параметр после неё
            sed -i "/^\[Desktop Entry\]/a DefaultProfile=$PROFILE_NAME_FOR_CONFIG" "$KONSOLERC"
            echo -e "\033[1;32m✓ Профиль \"$PROFILE_NAME\" установлен как основной\033[0m"
        else
            # Секции нет — добавляем секцию и параметр
            echo -e "\n[Desktop Entry]\nDefaultProfile=$PROFILE_NAME_FOR_CONFIG" >> "$KONSOLERC"
            echo -e "\033[1;32m✓ Профиль \"$PROFILE_NAME\" установлен как основной\033[0m"
        fi
    fi
fi

# ============================================================
# Удаляем себя из очереди
# ============================================================

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

# ============================================================
# Вывод информации для пользователя
# ============================================================

echo -e "\033[1;32m✅ Создание профиля Konsole завершено\033[0m"
echo -e "\033[1;33m→ Для применения изменений перезапустите Konsole (закройте и откройте заново).\033[0m"
echo -e "\033[1;33m→ Если профиль не применился автоматически, нажмите:\033[0m"
echo -e "\033[1;33m  ☰ (три точки вверху справа) → Сменить профиль → \"$PROFILE_NAME\"\033[0m"
