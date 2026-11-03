#!/bin/bash
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОткат: замедление мыши по кнопке 'вперед'\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Настройки (должны совпадать с установочным скриптом)
HOTKEY="Meta+Ctrl+Alt+1"
SCRIPT_DIR="$HOME/.local/share/kde-mouse-speed"
AUTOSTART_FILE="$HOME/.config/autostart/restore-mouse-speed.desktop"
APP_FILE="$HOME/.local/share/applications/net.local.toggle-mouse-speed.sh.desktop"
APP_NAME="net.local.toggle-mouse-speed.sh.desktop"
KGLOBAL_FILE="$HOME/.config/kglobalshortcutsrc"
KCM_FILE="$HOME/.config/kcminputrc"
STATE_FILE="$HOME/.config/kde_mouse_speed_state"

echo -e "\033[1;33m→ Проверка состояния мыши...\033[0m"
# Если мышь в замедленном режиме — восстанавливаем исходные скорости
if [ -f "$STATE_FILE" ]; then
    while IFS=: read -r dev original_speed slow_speed; do
        busctl --user set-property org.kde.KWin /org/kde/KWin/InputDevice/$dev org.kde.KWin.InputDevice pointerAcceleration d -- "$original_speed" 2>/dev/null
    done < "$STATE_FILE"
    rm -f "$STATE_FILE"
    echo -e "\033[1;32m✓ Скорость мыши восстановлена\033[0m"
fi

echo -e "\033[1;33m→ Удаление каталога со скриптами...\033[0m"
if [ -d "$SCRIPT_DIR" ]; then
    rm -rf "$SCRIPT_DIR"
    echo -e "\033[1;32m✓ Удалён каталог: $SCRIPT_DIR\033[0m"
fi

echo -e "\033[1;33m→ Удаление файла автостарта...\033[0m"
if [ -f "$AUTOSTART_FILE" ]; then
    rm -f "$AUTOSTART_FILE"
    echo -e "\033[1;32m✓ Удалён файл автостарта: $AUTOSTART_FILE\033[0m"
fi

echo -e "\033[1;33m→ Удаление .desktop файла приложения...\033[0m"
if [ -f "$APP_FILE" ]; then
    rm -f "$APP_FILE"
    echo -e "\033[1;32m✓ Удалён файл приложения: $APP_FILE\033[0m"
fi

echo -e "\033[1;33m→ Удаление записи из kglobalshortcutsrc...\033[0m"
if [ -f "$KGLOBAL_FILE" ]; then
    if grep -q "^\[services\]\[$APP_NAME\]" "$KGLOBAL_FILE" 2>/dev/null; then
        sed -i "/^\[services\]\[$APP_NAME\]/,/^\[/{/^\[services\]\[$APP_NAME\]/d;/^\[/!d}" "$KGLOBAL_FILE"
        echo -e "\033[1;32m✓ Удалена запись из: $KGLOBAL_FILE\033[0m"
    fi
fi

echo -e "\033[1;33m→ Удаление привязки кнопки мыши из kcminputrc...\033[0m"
if [ -f "$KCM_FILE" ]; then
    if grep -q "^ExtraButton2=Key,$HOTKEY$" "$KCM_FILE" 2>/dev/null; then
        sed -i "/^ExtraButton2=Key,$HOTKEY$/d" "$KCM_FILE"
        echo -e "\033[1;32m✓ Удалена привязка кнопки ExtraButton2 из: $KCM_FILE\033[0m"
    else
        echo -e "\033[1;33m⚠ Привязка кнопки ExtraButton2 не найдена или была изменена пользователем\033[0m"
    fi
fi

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Откат завершён успешно\033[0m"
echo ""
echo -e "\033[1;33mДля полного применения изменений необходимо выйти из сеанса и снова войти, или просто перезагрузить компьютер.\033[0m"
