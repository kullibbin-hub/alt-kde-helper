#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУдаление VirtualBox и восстановление KVM\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Запрос подтверждения
kdialog --title "Удаление VirtualBox" \
        --yesno "Будет выполнено удаление VirtualBox и модулей ядра.\n\nПоддержка KVM будет восстановлена.\n\nПродолжить?"

if [ $? -ne 0 ]; then
    echo -e "\033[1;33m⚠ Удаление VirtualBox отменено пользователем\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

# Удаление VirtualBox и модулей ядра
echo -e "\033[1;33m→ Удаление VirtualBox и модулей ядра...\033[0m"
sudo apt-get remove -y virtualbox "kernel-modules-virtualbox-*"

if [ $? -eq 0 ]; then
    echo -e "\033[1;32m✓ VirtualBox и модули ядра удалены\033[0m"
else
    echo -e "\033[1;33m⚠ Возникла ошибка при удалении, но продолжаем...\033[0m"
fi

# Восстановление KVM — удаляем чёрный список
if [ -f /etc/modprobe.d/blacklist-kvm-for-virtualbox.conf ]; then
    echo -e "\033[1;33m→ Восстановление поддержки KVM...\033[0m"
    sudo rm -f /etc/modprobe.d/blacklist-kvm-for-virtualbox.conf
    echo -e "\033[1;32m✓ Файл чёрного списка KVM удалён\033[0m"
    echo -e "\033[1;33m→ KVM будет доступен после перезагрузки\033[0m"
else
    echo -e "\033[1;33m→ Файл чёрного списка KVM не найден, пропускаем\033[0m"
fi

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m========================================\033[0m"
echo -e "\033[1;32m✅ Удаление VirtualBox завершено!\033[0m"
echo -e "\033[1;32m========================================\033[0m"
echo -e "\033[1;33m→ Для полного восстановления KVM рекомендуется перезагрузить систему\033[0m"

kdialog --title "Удаление VirtualBox" \
        --msgbox "Удаление VirtualBox завершено!\n\nДля полного восстановления KVM рекомендуется перезагрузить систему."
