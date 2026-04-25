#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОбновление eepm\033[0m"
echo -e "\033[1;36m========================================\033[0m"

ERROR=0

echo -e "\033[1;33m→ Обновление eepm...\033[0m"
sudo epm upgrade "https://download.etersoft.ru/pub/Korinf/x86_64/ALTLinux/p11/eepm-*.noarch.rpm"
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить eepm\033[0m"
    ERROR=1
else
    echo -e "\033[1;32m✓ eepm обновлён\033[0m"
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
