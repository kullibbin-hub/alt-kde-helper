#!/bin/bash
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mЗамедление мыши по кнопке 'вперед'\033[0m"
echo -e "\033[1;36m========================================\033[0m"

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
FLAG_FILE="$STATE_DIR/$(basename "$0")"

# Удаляем старый флаг
rm -f "$FLAG_FILE"

# Настройки
HOTKEY="Meta+Ctrl+Alt+1"
SCRIPT_DIR="$HOME/.local/share/kde-mouse-speed"
AUTOSTART_DIR="$HOME/.config/autostart"
APP_DIR="$HOME/.local/share/applications"
APP_NAME="net.local.toggle-mouse-speed.sh.desktop"

echo -e "\033[1;33m→ Создание каталогов...\033[0m"
mkdir -p "$SCRIPT_DIR"
mkdir -p "$AUTOSTART_DIR"
mkdir -p "$APP_DIR"

echo -e "\033[1;33m→ Создание основного скрипта переключения скорости...\033[0m"
cat > "$SCRIPT_DIR/toggle-mouse-speed.sh" << 'EOF'
#!/bin/bash
STATE_FILE="$HOME/.config/kde_mouse_speed_state"

# Проверяем наличие флага
if [ -f "$STATE_FILE" ]; then
    # Флаг есть — восстанавливаем исходные скорости для каждой мыши
    while IFS=: read -r dev original_speed slow_speed; do
        busctl --user set-property org.kde.KWin /org/kde/KWin/InputDevice/$dev org.kde.KWin.InputDevice pointerAcceleration d -- "$original_speed"
    done < "$STATE_FILE"
    rm -f "$STATE_FILE"
    notify-send -i mouse "Скорость мыши" "Обычный режим"
else
    # Флага нет — сохраняем текущие скорости всех мышей и вычисляем замедленные
    > "$STATE_FILE"
    for dev in $(busctl --user get-property org.kde.KWin /org/kde/KWin/InputDevice org.kde.KWin.InputDeviceManager devicesSysNames | grep -oE '"[^"]+"'); do
        dev_clean=$(echo $dev | tr -d '"')
        supports=$(busctl --user get-property org.kde.KWin /org/kde/KWin/InputDevice/$dev_clean org.kde.KWin.InputDevice supportsPointerAcceleration 2>/dev/null | awk '{print $2}')
        touchpad=$(busctl --user get-property org.kde.KWin /org/kde/KWin/InputDevice/$dev_clean org.kde.KWin.InputDevice touchpad 2>/dev/null | awk '{print $2}')

        if [ "$supports" = "true" ] && [ "$touchpad" != "true" ]; then
            current_speed=$(busctl --user get-property org.kde.KWin /org/kde/KWin/InputDevice/$dev_clean org.kde.KWin.InputDevice pointerAcceleration 2>/dev/null | awk '{print $2}')

            # Вычисляем замедленную скорость для этой мыши: new = -1.0 + (current + 1.0) / 3
            slow_speed=$(echo "$current_speed" | awk '{printf "%.2f", -1.0 + ($1 + 1.0) / 3}')

            # Сохраняем тройку: устройство:исходная_скорость:замедленная_скорость
            echo "$dev_clean:$current_speed:$slow_speed" >> "$STATE_FILE"

            # Применяем замедленную скорость
            busctl --user set-property org.kde.KWin /org/kde/KWin/InputDevice/$dev_clean org.kde.KWin.InputDevice pointerAcceleration d -- "$slow_speed"
        fi
    done
    notify-send -i mouse "Скорость мыши" "Медленный режим"
fi
EOF

echo -e "\033[1;33m→ Создание скрипта восстановления при загрузке...\033[0m"
cat > "$SCRIPT_DIR/restore-mouse-speed.sh" << 'EOF'
#!/bin/bash
STATE_FILE="$HOME/.config/kde_mouse_speed_state"

# Ждём, пока KWin будет готов
sleep 3

# Проверяем наличие файла состояния
if [ -f "$STATE_FILE" ]; then
    # Файл есть — восстанавливаем исходные скорости для каждой мыши
    while IFS=: read -r dev original_speed slow_speed; do
        busctl --user set-property org.kde.KWin /org/kde/KWin/InputDevice/$dev org.kde.KWin.InputDevice pointerAcceleration d -- "$original_speed"
    done < "$STATE_FILE"
    rm -f "$STATE_FILE"
fi
EOF

echo -e "\033[1;33m→ Установка прав на скрипты...\033[0m"
chmod +x "$SCRIPT_DIR/toggle-mouse-speed.sh"
chmod +x "$SCRIPT_DIR/restore-mouse-speed.sh"

echo -e "\033[1;33m→ Создание .desktop файла для автостарта...\033[0m"
cat > "$AUTOSTART_DIR/restore-mouse-speed.desktop" << EOF
[Desktop Entry]
Exec=$SCRIPT_DIR/restore-mouse-speed.sh
Icon=application-x-executable-script
Name=restore-mouse-speed.sh
Type=Application
X-KDE-AutostartScript=true
EOF

echo -e "\033[1;33m→ Создание .desktop файла для глобального сочетания клавиш...\033[0m"
cat > "$APP_DIR/$APP_NAME" << EOF
[Desktop Entry]
Exec=$SCRIPT_DIR/toggle-mouse-speed.sh
Name=toggle-mouse-speed
NoDisplay=true
StartupNotify=false
Type=Application
X-KDE-GlobalAccel-CommandShortcut=true
EOF

echo -e "\033[1;33m→ Регистрация сочетания клавиш...\033[0m"
KGLOBAL_FILE="$HOME/.config/kglobalshortcutsrc"

# Удаляем старую секцию, если есть
if grep -q "^\[services\]\[$APP_NAME\]" "$KGLOBAL_FILE" 2>/dev/null; then
    sed -i "/^\[services\]\[$APP_NAME\]/,/^\[/{/^\[services\]\[$APP_NAME\]/d;/^\[/!d}" "$KGLOBAL_FILE"
fi

# Добавляем новую секцию в конец файла
{
    echo ""
    echo "[services][$APP_NAME]"
    echo "_launch=$HOTKEY"
} >> "$KGLOBAL_FILE"

# Перезапускаем kglobalaccel, чтобы применить изменения
systemctl --user restart plasma-kglobalaccel.service 2>/dev/null || true

echo -e "\033[1;33m→ Привязка кнопки 'Вперёд' (ExtraButton2) к сочетанию клавиш...\033[0m"
kwriteconfig6 --file kcminputrc --group "ButtonRebinds" --group "Mouse" --key "ExtraButton2" "Key,$HOTKEY"

# Уведомляем KDE об изменении настроек мыши
dbus-send --session --dest=org.kde.KCModuleMouse --type=method_call /kcminput org.kde.KCMModuleMouse.reconfigure 2>/dev/null || true

# Создаём флаг успешной установки
touch "$FLAG_FILE"
echo -e "\033[1;32m✓ Флаг установки создан\033[0m"

# Удаляем себя из очереди
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Установка завершена успешно\033[0m"
echo ""
echo -e "\033[1;32mУстановлено:\033[0m"
echo "  Скрипты: $SCRIPT_DIR"
echo "  Автостарт: $AUTOSTART_DIR/restore-mouse-speed.desktop"
echo "  Глобальное сочетание: $HOTKEY"
echo "  Кнопка 'Вперёд' (ExtraButton2) привязана к сочетанию $HOTKEY"
echo ""
echo -e "\033[1;33mДля полного применения изменений требуется перелогин.\033[0m"
echo ""
echo -e "\033[1;32mКак это работает:\033[0m"
echo "  - Нажатие кнопки 'Вперёд' переключает скорость мыши (обычная / замедленная)"
echo "  - Замедление применяется только к мышам, тачпад не затрагивается"
echo "  - Для каждой мыши своя исходная скорость сохраняется и восстанавливается"
echo "  - При перезагрузке с активной замедленной скоростью — она автоматически восстановится при входе"
echo ""
echo -e "\033[1;32mПереназначение кнопки:\033[0m"
echo "  Параметры системы → Мышь и сенсорная панель → Настроить дополнительные кнопки"
echo "  и назначить на нужную кнопку сочетание клавиш $HOTKEY"
echo ""
echo -e "\033[1;33mДля полного применения изменений необходимо выйти из сеанса и снова войти, или просто перезагрузить компьютер.\033[0m"
