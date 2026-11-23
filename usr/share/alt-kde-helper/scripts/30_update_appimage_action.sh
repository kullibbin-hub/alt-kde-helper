#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОбновление AppImage через Gear Lever\033[0m"
echo -e "\033[1;36m========================================\033[0m"

GEARLEVER_CMD=""
if command -v gearlever >/dev/null 2>&1; then
    GEARLEVER_CMD="gearlever"
elif flatpak list 2>/dev/null | grep -q "it.mijorus.gearlever"; then
    GEARLEVER_CMD="flatpak run it.mijorus.gearlever"
fi

ERROR_OCCURRED=false

if [ -n "$GEARLEVER_CMD" ]; then
    echo -e "\033[1;33m→ Получение списка обновлений...\033[0m"
    UPDATE_LIST=$($GEARLEVER_CMD --list-updates)

    if [ -z "$UPDATE_LIST" ]; then
        echo -e "\033[1;32m✓ Gear Lever: обновлений нет\033[0m"
    else
        UPDATE_PATHS=$(echo "$UPDATE_LIST" | sed -E 's/.*\][[:space:]]+//; s/[[:space:]]+$//')

        get_running_with_updates() {
            local ps_out result path
            ps_out=$(ps -eo args= 2>/dev/null)
            result=""
            while IFS= read -r path; do
                [ -z "$path" ] && continue
                if echo "$ps_out" | grep -qF -- "$path"; then
                    result="${result}  • $(basename "$path")"$'\n'
                fi
            done <<< "$UPDATE_PATHS"
            printf '%s' "${result%$'\n'}"
        }

        GEARLEVER_SKIP=false
        while true; do
            RUNNING=$(get_running_with_updates)
            [ -z "$RUNNING" ] && break

            echo -e "\033[1;33m⚠ Запущены программы с обновлениями\033[0m"
            kdialog --yesno "Перед обновлением AppImage закройте следующие запущенные программы, для которых есть обновления:
${RUNNING}

Пока они открыты, их файлы заблокированы системой, и обновление для них не установится.
Сохраните работу и закройте их вручную.

Готово?
Если нет — обновление AppImage будет пропущено." 2>/dev/null
            if [ $? -ne 0 ]; then
                echo -e "\033[1;33m⚠ Обновление AppImage отложено пользователем, пропуск\033[0m"
                GEARLEVER_SKIP=true
                break
            fi
        done

        if [ "$GEARLEVER_SKIP" = false ]; then
            echo -e "\033[1;33m→ Обновление AppImage через Gear Lever...\033[0m"
            $GEARLEVER_CMD --update --all -y
            if [ $? -ne 0 ]; then
                echo -e "\033[1;31m❌ Ошибка: не удалось обновить AppImage через Gear Lever\033[0m"
                ERROR_OCCURRED=true
            else
                echo -e "\033[1;32m✓ Gear Lever: обновление выполнено\033[0m"
            fi
        fi
    fi
else
    echo -e "\033[1;33m⚠ Gear Lever не установлен, пропуск\033[0m"
fi

# ---------- AppMan ----------
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОбновление AppImage через appman\033[0m"
echo -e "\033[1;36m========================================\033[0m"

if command -v appman >/dev/null 2>&1; then
    echo -e "\033[1;33m→ Обновление через appman...\033[0m"
    appman update
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ Ошибка: не удалось обновить AppImage через appman\033[0m"
        ERROR_OCCURRED=true
    else
        echo -e "\033[1;32m✓ appman: обновление выполнено\033[0m"
    fi
else
    echo -e "\033[1;33m⚠ appman не установлен, пропуск\033[0m"
fi

# ---------- Итог ----------
if [ "$ERROR_OCCURRED" = true ]; then
    echo -e "\033[1;31m❌ Один из этапов завершился с ошибкой. Очередь не очищена.\033[0m"
    exit 1
else
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    echo -e "\033[1;32m✅ Обновление AppImage завершено\033[0m"
    exit 0
fi
