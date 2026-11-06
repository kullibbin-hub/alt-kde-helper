#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОчистка данных удалённых Flatpak-приложений\033[0m"
echo -e "\033[1;36m========================================\033[0m"

FLATPAK_APP_DATA_DIR="$HOME/.var/app"

cleanup_and_exit() {
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
}

if [ ! -d "$FLATPAK_APP_DATA_DIR" ]; then
    echo -e "\033[1;32m✅ Данных от удалённых приложений не найдено.\033[0m"
    cleanup_and_exit
fi

echo -e "\033[1;33m→ Поиск данных от приложений Flatpak, которых нет в системе...\033[0m"

orphan_apps=()
for app_dir in "$FLATPAK_APP_DATA_DIR"/*/; do
    [ -d "$app_dir" ] || continue
    app_id="${app_dir%/}"
    app_id="${app_id##*/}"
    if ! flatpak info "$app_id" &>/dev/null; then
        orphan_apps+=("$app_id")
    fi
done

if [ ${#orphan_apps[@]} -eq 0 ]; then
    echo -e "\033[1;32m✅ Данных от удалённых приложений не найдено.\033[0m"
    cleanup_and_exit
fi

# Локальные имена из AppStream
declare -A app_names=()
if command -v xmlstarlet >/dev/null 2>&1; then
    for xml_file in /var/lib/flatpak/appstream/*/*/active/appstream.xml; do
        [ -f "$xml_file" ] || continue
        while IFS='|' read -r id name; do
            [ -n "$id" ] && [ -n "$name" ] && app_names["$id"]="$name"
        done < <(xmlstarlet sel -t -m "//component" -v "id" -o "|" \
                        -v "name[not(@xml:lang)]" -n "$xml_file" 2>/dev/null)
    done
fi

# Онлайн-фоллбэк через Flathub API для тех, кому локального имени не хватило
if command -v curl >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    for app_id in "${orphan_apps[@]}"; do
        [ -n "${app_names[$app_id]}" ] && continue
        name=$(curl -sf --max-time 5 "https://flathub.org/api/v2/appstream/$app_id" \
               | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)
        [ -n "$name" ] && app_names["$app_id"]="$name"
    done
fi

echo -e "\033[1;33m→ Найдено: ${#orphan_apps[@]}\033[0m"
echo ""
for app_id in "${orphan_apps[@]}"; do
    if [ -n "${app_names[$app_id]}" ]; then
        echo "  • ${app_names[$app_id]} — $app_id"
    else
        echo "  • $app_id"
    fi
done
echo ""

if kdialog --yesno "Найдены данные для отсутствующих приложений из Flatpak. Удалить? Удаленные папки помещаются в корзину, откуда вы можете восстановить те, которые нужны."; then
    removed=0
    for app_id in "${orphan_apps[@]}"; do
        if gio trash -- "$FLATPAK_APP_DATA_DIR/$app_id" 2>/dev/null; then
            echo -e "  \033[0;32m✅ Перемещено в корзину: $app_id\033[0m"
            removed=$((removed + 1))
        else
            echo -e "  \033[1;33m⚠ Не удалось переместить в корзину: $app_id\033[0m"
        fi
    done
    echo ""
    echo -e "\033[1;32m✅ Готово. Перемещено в корзину: $removed из ${#orphan_apps[@]}.\033[0m"
else
    echo -e "\033[1;33m⏭ Отменено пользователем. Ничего не удалено.\033[0m"
fi

cleanup_and_exit
