#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОчистка кэша\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Проверка наличия stmpclean
STMPCLEAN_OK=0
if sudo which stmpclean &>/dev/null; then
    STMPCLEAN_OK=1
    echo -e "\033[1;32m✓ stmpclean уже установлен\033[0m"
else
    echo -e "\033[1;33m→ stmpclean не установлен. Попытка установки...\033[0m"
    sudo apt-get update 2>/dev/null
    sudo apt-get install -y stmpclean 2>/dev/null
    if sudo which stmpclean &>/dev/null; then
        STMPCLEAN_OK=1
        echo -e "\033[1;32m✓ stmpclean успешно установлен\033[0m"
    else
        echo -e "\033[1;33m⚠ stmpclean не установлен. Очистка /tmp и /var/tmp будет пропущена\033[0m"
    fi
fi

# Функция для получения used в KB
get_used_kb() {
    df -k "$1" 2>/dev/null | tail -1 | awk '{print $3}'
}

# Функция для получения total в KB
get_total_kb() {
    df -k "$1" 2>/dev/null | tail -1 | awk '{print $2}'
}

# Сохраняем состояние ДО очистки
ROOT_TOTAL_KB=$(get_total_kb "/")
ROOT_BEFORE_KB=$(get_used_kb "/")
HOME_TOTAL_KB=$(get_total_kb "/home")
HOME_BEFORE_KB=$(get_used_kb "/home")

# Очистка
echo -e "\033[1;33m→ Очистка кэша APT...\033[0m"
sudo apt-get clean

if [ $STMPCLEAN_OK -eq 1 ]; then
    echo -e "\033[1;33m→ Очистка временных файлов /tmp...\033[0m"
    sudo stmpclean /tmp

    echo -e "\033[1;33m→ Очистка временных файлов /var/tmp...\033[0m"
    sudo stmpclean /var/tmp
else
    echo -e "\033[1;33m⚠ Очистка /tmp и /var/tmp пропущена (stmpclean не установлен)\033[0m"
fi

echo -e "\033[1;33m→ Очистка старых системных журналов (оставляем 100 МБ)...\033[0m"
sudo journalctl --vacuum-size=100M

echo -e "\033[1;33m→ Очистка кэша пользователя...\033[0m"
rm -rf ~/.cache/*

echo -e "\033[1;33m→ Очистка кэша Flatpak...\033[0m"
rm -rf ~/.var/app/*/cache/*

echo -e "\033[1;33m→ Удаление неиспользуемых рантаймов Flatpak...\033[0m"
flatpak uninstall --unused -y 2>/dev/null

echo -e "\033[1;33m→ Удаление старых, неиспользуемых ядер...\033[0m"
sudo remove-old-kernels -y 2>/dev/null

echo -e "\033[1;33m→ Очистка временных файлов Audacity...\033[0m"
sudo rm -rf /var/tmp/audacity-*

# Получаем состояние ПОСЛЕ очистки
ROOT_AFTER_KB=$(get_used_kb "/")
HOME_AFTER_KB=$(get_used_kb "/home")

# Функция вывода отчёта для раздела
print_report() {
    local name="$1"
    local mount="$2"
    local total_kb="$3"
    local before_kb="$4"
    local after_kb="$5"

    total_gb=$(echo "scale=1; $total_kb / 1024 / 1024" | bc)
    before_gb=$(echo "scale=1; $before_kb / 1024 / 1024" | bc)
    after_gb=$(echo "scale=1; $after_kb / 1024 / 1024" | bc)
    before_percent=$(echo "scale=0; $before_kb * 100 / $total_kb" | bc)
    after_percent=$(echo "scale=0; $after_kb * 100 / $total_kb" | bc)
    freed_kb=$((before_kb - after_kb))
    freed_mb=$(echo "scale=0; $freed_kb / 1024" | bc)

    echo -e "\033[1;36m→ $name ($mount):\033[0m"
    echo -e "  \033[1;36mОбщая ёмкость:\033[0m ${total_gb} ГБ"
    echo -e "  \033[1;33mДо очистки:\033[0m    ${before_gb} ГБ (${before_percent}%)"
    echo -e "  \033[1;32mПосле очистки:\033[0m ${after_gb} ГБ (${after_percent}%)"
    if [ $freed_mb -gt 0 ]; then
        echo -e "  \033[1;32mОчищено:\033[0m       ${freed_mb} МБ"
    else
        echo -e "  \033[1;32mОчищено:\033[0m       0 МБ"
    fi
    echo ""
}

# Выводим отчёт
echo -e "\033[1;36m"
echo "========================================="
echo "          ОТЧЁТ ОБ ОЧИСТКЕ"
echo "========================================="
echo -e "\033[0m"

print_report "Корневой раздел" "/" "$ROOT_TOTAL_KB" "$ROOT_BEFORE_KB" "$ROOT_AFTER_KB"
print_report "Домашний раздел" "/home" "$HOME_TOTAL_KB" "$HOME_BEFORE_KB" "$HOME_AFTER_KB"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Очистка кэша завершена\033[0m"
