#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОбновление eepm\033[0m"
echo -e "\033[1;36m========================================\033[0m"

if ! command -v epm >/dev/null 2>&1; then
    echo -e "\033[1;33m⚠ eepm не установлен — обновление пропущено\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

ERROR=0
# Ветка репозитория etersoft: для Сизифа используется "Sisyphus", для стабильных веток "p<версия>"
if grep -qi 'sisyphus' /etc/os-release; then
    VER="Sisyphus"
else
    VER=$(grep -E '^VERSION_ID=' /etc/os-release | cut -d= -f2 | tr -d '"' | cut -d. -f1)
fi

if [ -z "$VER" ]; then
    echo -e "\033[1;31m❌ Не удалось определить версию системы\033[0m"
    ERROR=1
else
    if [ "$VER" = "Sisyphus" ]; then
        REMOTE_URL="https://download.etersoft.ru/pub/Korinf/x86_64/ALTLinux/Sisyphus/"
    else
        REMOTE_URL="https://download.etersoft.ru/pub/Korinf/x86_64/ALTLinux/p${VER}/"
    fi

    echo -e "\033[1;33m→ Получение информации о версиях...\033[0m"
    PAGE=$(wget -qO- --timeout=10 "$REMOTE_URL")

    LOCAL_EEPM=$(rpm -q --qf '%{NAME}-%{VERSION}' eepm 2>/dev/null)
    LOCAL_REPACK=$(rpm -q --qf '%{NAME}-%{VERSION}' eepm-repack 2>/dev/null)

    REMOTE_EEPM=$(echo "$PAGE" | grep -oE 'eepm-[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
    FILENAME_EEPM=$(echo "$PAGE" | grep -oE "${REMOTE_EEPM}-[^\"]+\.noarch\.rpm" | head -n 1)

    if [ -n "$LOCAL_REPACK" ]; then
        REMOTE_REPACK=$(echo "$PAGE" | grep -oE 'eepm-repack-[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
        FILENAME_REPACK=$(echo "$PAGE" | grep -oE "${REMOTE_REPACK}-[^\"]+\.noarch\.rpm" | head -n 1)
    fi

    LOCAL_VER_EEPM="${LOCAL_EEPM#eepm-}"
    LOCAL_VER_REPACK="${LOCAL_REPACK#eepm-repack-}"
    REMOTE_VER_EEPM="${REMOTE_EEPM#eepm-}"
    REMOTE_VER_REPACK="${REMOTE_REPACK#eepm-repack-}"

    [ -n "$LOCAL_EEPM" ]   && echo -e "  Установленный eepm:        $LOCAL_EEPM"
    [ -n "$LOCAL_REPACK" ] && echo -e "  Установленный eepm-repack: $LOCAL_REPACK"
    [ -n "$REMOTE_EEPM" ]   && echo -e "  Доступный eepm:            $REMOTE_EEPM"
    [ -n "$REMOTE_REPACK" ] && echo -e "  Доступный eepm-repack:     $REMOTE_REPACK"

    if [ -z "$REMOTE_EEPM" ] || [ -z "$FILENAME_EEPM" ]; then
        if [ -n "$LOCAL_REPACK" ]; then
            echo -e "\033[1;33m⚠ Не удалось получить данные с сервера\033[0m"
            echo -e "\033[1;33m⚠ eepm-repack установлен — обновление пропущено,\033[0m"
            echo -e "\033[1;33m  чтобы не сломать зависимости и не удалить пакеты\033[0m"
            ERROR=1
        else
            echo -e "\033[1;33m⚠ Не удалось получить версию с сервера, выполняется принудительное обновление\033[0m"
            echo -e "\033[1;33m→ Обновление eepm...\033[0m"
            sudo epm upgrade "$REMOTE_URL/eepm-*.noarch.rpm"
            if [ $? -ne 0 ]; then
                echo -e "\033[1;31m❌ Ошибка: не удалось обновить eepm\033[0m"
                ERROR=1
            else
                echo -e "\033[1;32m✓ eepm обновлён\033[0m"
            fi
        fi
    elif [ -n "$LOCAL_REPACK" ] && { [ -z "$REMOTE_REPACK" ] || [ -z "$FILENAME_REPACK" ] || [ "$REMOTE_VER_EEPM" != "$REMOTE_VER_REPACK" ]; }; then
        echo -e "\033[1;33m⚠ На сервере неполный комплект: eepm есть,\033[0m"
        echo -e "\033[1;33m  но eepm-repack отсутствует или версии не совпадают\033[0m"
        echo -e "\033[1;33m⚠ Обновление пропущено, чтобы не удалить\033[0m"
        echo -e "\033[1;33m  eepm-repack и eepm-play-gui\033[0m"
        ERROR=1
    elif [ "$LOCAL_VER_EEPM" = "$REMOTE_VER_EEPM" ] && { [ -z "$LOCAL_REPACK" ] || [ "$LOCAL_VER_REPACK" = "$REMOTE_VER_REPACK" ]; }; then
        echo -e "\033[1;32m✓ eepm уже актуален, обновление не требуется\033[0m"
    else
        if [ -n "$LOCAL_REPACK" ]; then
            echo -e "\033[1;33m→ Обновление eepm и eepm-repack ($LOCAL_VER_EEPM → $REMOTE_VER_EEPM)...\033[0m"
            sudo epm upgrade "$REMOTE_URL/$FILENAME_EEPM" "$REMOTE_URL/$FILENAME_REPACK"
        else
            echo -e "\033[1;33m→ Обновление eepm ($LOCAL_VER_EEPM → $REMOTE_VER_EEPM)...\033[0m"
            sudo epm upgrade "$REMOTE_URL/$FILENAME_EEPM"
        fi
        if [ $? -ne 0 ]; then
            echo -e "\033[1;31m❌ Ошибка: не удалось обновить eepm\033[0m"
            ERROR=1
        else
            echo -e "\033[1;32m✓ eepm обновлён\033[0m"
        fi
    fi
fi

echo -e "\033[1;33m→ Обновление софта, установленного через epm play...\033[0m"
sudo epm play --update all
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить софт epm play\033[0m"
    ERROR=1
else
    echo -e "\033[1;32m✓ Софт epm play обновлён\033[0m"
fi

# Если ошибок не было - удаляем себя из очереди
if [ $ERROR -eq 0 ]; then
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    echo -e "\033[1;32m✅ Обновление eepm успешно завершено\033[0m"
else
    echo -e "\033[1;33m⚠ Были ошибки, скрипт останется в очереди для повторной попытки\033[0m"
fi
