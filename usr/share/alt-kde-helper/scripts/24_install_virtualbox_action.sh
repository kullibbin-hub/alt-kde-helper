#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка VirtualBox и дополнений\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Получаем flavour текущего ядра (например, 6.12)
CURRENT_KERNEL_FLAVOUR=$(uname -r | cut -d '.' -f1,2)

echo -e "\033[1;33m→ Текущий flavour ядра: $CURRENT_KERNEL_FLAVOUR\033[0m"

# Проверяем наличие модуля VirtualBox для текущего flavour ядра
if apt-cache search --names-only "^kernel-modules-virtualbox-$CURRENT_KERNEL_FLAVOUR" | grep -q "kernel-modules-virtualbox-$CURRENT_KERNEL_FLAVOUR"; then
    echo -e "\033[1;32m✓ Модуль VirtualBox для ядра $CURRENT_KERNEL_FLAVOUR найден\033[0m"
else
    echo -e "\033[1;31m❌ Ошибка: Модуль VirtualBox для ядра $CURRENT_KERNEL_FLAVOUR не найден в репозитории\033[0m"
    echo -e "\033[1;33m→ Для установки VirtualBox требуется обновить ядро\033[0m"
    echo -e "\033[1;33m→ Пожалуйста, выполните обновление ядра через пункт 'Обновление ядра и модулей' в разделе 'Обслуживание', перезагрузите компьютер, а затем повторите установку VirtualBox. Если ядро было недавно обновлено, попробуйте наоборот, выбрать предыдущее ядро при загрузке, в меню загрузчика (Grub) при включении компьютера.\033[0m"
    kdialog --title "Установка VirtualBox" \
            --error "Модуль VirtualBox для ядра $CURRENT_KERNEL_FLAVOUR не найден.\n\nДля установки VirtualBox требуется обновить ядро.\n\nПожалуйста, выполните обновление ядра через пункт 'Обновление ядра и модулей' в разделе 'Обслуживание', перезагрузите компьютер, а затем повторите установку.\nЕсли ядро было недавно обновлено, попробуйте наоборот, выбрать предыдущее ядро при загрузке, в меню загрузчика (Grub) при включении компьютера."
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 1
fi

# Запрос подтверждения
kdialog --title "Установка VirtualBox" \
        --yesno "Будет выполнена установка VirtualBox со следующими компонентами:\n\n• VirtualBox\n• Модули ядра для текущего ядра\n• Oracle Extension Pack\n• Гостевые дополнения (ISO)\n\nТакже будет отключена поддержка KVM (для совместимости).\n\nПродолжить?"

if [ $? -ne 0 ]; then
    echo -e "\033[1;33m⚠ Установка VirtualBox отменена пользователем\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

# Установка основного пакета и модуля ядра
echo -e "\033[1;33m→ Установка VirtualBox и модулей ядра...\033[0m"
sudo apt-get update
sudo apt-get install -y virtualbox "kernel-modules-virtualbox-$CURRENT_KERNEL_FLAVOUR"

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка при установке VirtualBox или модулей ядра\033[0m"
    kdialog --title "Ошибка" --error "Не удалось установить VirtualBox или модули ядра."
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 1
fi

# Добавление пользователя в группу vboxusers
echo -e "\033[1;33m→ Добавление пользователя в группу vboxusers...\033[0m"
sudo usermod -aG vboxusers "$(whoami)"
echo -e "\033[1;32m✓ Пользователь добавлен в группу vboxusers\033[0m"

# Отключение KVM через чёрный список
echo -e "\033[1;33m→ Отключение поддержки KVM (для совместимости с VirtualBox)...\033[0m"

# Определяем, какой модуль KVM загружен
if lsmod | grep -q kvm_intel; then
    KVM_MODULE="kvm_intel"
elif lsmod | grep -q kvm_amd; then
    KVM_MODULE="kvm_amd"
else
    KVM_MODULE=""
fi

if [ -n "$KVM_MODULE" ]; then
    # Создаём файл чёрного списка
    echo "blacklist $KVM_MODULE" | sudo tee /etc/modprobe.d/blacklist-kvm-for-virtualbox.conf > /dev/null
    echo -e "\033[1;32m✓ Модуль $KVM_MODULE добавлен в чёрный список\033[0m"

    # Выгружаем модуль из текущей сессии
    sudo rmmod "$KVM_MODULE" 2>/dev/null
    echo -e "\033[1;32m✓ Модуль $KVM_MODULE выгружен\033[0m"
else
    echo -e "\033[1;33m→ KVM не обнаружен, отключение не требуется\033[0m"
fi

# Определяем версию VirtualBox
if command -v vboxmanage &>/dev/null; then
    VB_VERSION=$(vboxmanage --version | cut -d'r' -f1)
else
    # Если vboxmanage ещё не доступен, получаем версию из установленного пакета
    VB_VERSION=$(rpm -q virtualbox --queryformat "%{VERSION}" 2>/dev/null | cut -d'-' -f1)
fi

echo -e "\033[1;33m→ Версия VirtualBox: $VB_VERSION\033[0m"

# Определяем папку загрузок
DOWNLOAD_DIR=$(xdg-user-dir DOWNLOAD 2>/dev/null)
if [ -z "$DOWNLOAD_DIR" ] || [ ! -d "$DOWNLOAD_DIR" ]; then
    DOWNLOAD_DIR="$HOME/Загрузки"
fi

# Скачивание Extension Pack
EXT_PACK_URL="https://download.virtualbox.org/virtualbox/$VB_VERSION/Oracle_VirtualBox_Extension_Pack-$VB_VERSION.vbox-extpack"
EXT_PACK_FILE="$DOWNLOAD_DIR/Oracle_VirtualBox_Extension_Pack-$VB_VERSION.vbox-extpack"

echo -e "\033[1;33m→ Скачивание Extension Pack...\033[0m"
if [ -f "$EXT_PACK_FILE" ]; then
    echo -e "\033[1;32m✓ Extension Pack уже скачан: $EXT_PACK_FILE\033[0m"
else
    if wget -q --show-progress -O "$EXT_PACK_FILE" "$EXT_PACK_URL"; then
        echo -e "\033[1;32m✓ Extension Pack скачан: $EXT_PACK_FILE\033[0m"
    else
        echo -e "\033[1;31m❌ Не удалось скачать Extension Pack\033[0m"
    fi
fi

# Установка Extension Pack
if [ -f "$EXT_PACK_FILE" ]; then
    kdialog --title "Лицензионное соглашение Oracle Extension Pack" \
            --warningcontinuecancel "Oracle VM VirtualBox Extension Pack распространяется под проприетарной лицензией PUEL.\n\nБесплатно для личного и образовательного некоммерческого использования.\n\nПодробнее: https://www.virtualbox.org/wiki/ExtensionPack\n\nПродолжить установку?"

    if [ $? -eq 0 ]; then
        echo -e "\033[1;33m→ Установка Extension Pack...\033[0m"
        echo y | vboxmanage extpack install --replace "$EXT_PACK_FILE"
        if [ $? -eq 0 ]; then
            echo -e "\033[1;32m✓ Extension Pack установлен\033[0m"
        else
            echo -e "\033[1;33m⚠ Ошибка при установке Extension Pack\033[0m"
        fi
    else
        echo -e "\033[1;33m⚠ Установка Extension Pack отменена пользователем\033[0m"
    fi
fi

# Скачивание Guest Additions ISO
GUEST_ADDITIONS_URL="https://download.virtualbox.org/virtualbox/$VB_VERSION/VBoxGuestAdditions_$VB_VERSION.iso"
GUEST_ADDITIONS_FILE="$DOWNLOAD_DIR/VBoxGuestAdditions_$VB_VERSION.iso"

echo -e "\033[1;33m→ Скачивание гостевых дополнений...\033[0m"
if [ -f "$GUEST_ADDITIONS_FILE" ]; then
    echo -e "\033[1;32m✓ Гостевые дополнения уже скачаны: $GUEST_ADDITIONS_FILE\033[0m"
else
    if wget -q --show-progress -O "$GUEST_ADDITIONS_FILE" "$GUEST_ADDITIONS_URL"; then
        echo -e "\033[1;32m✓ Гостевые дополнения скачаны: $GUEST_ADDITIONS_FILE\033[0m"
    else
        echo -e "\033[1;31m❌ Не удалось скачать гостевые дополнения\033[0m"
    fi
fi

echo -e "\033[1;33m→ Гостевые дополнения (VBoxGuestAdditions.iso) сохранены в папку $DOWNLOAD_DIR\033[0m"

# Запуск сервиса VirtualBox
echo -e "\033[1;33m→ Запуск сервиса VirtualBox...\033[0m"
sudo systemctl start virtualbox.service 2>/dev/null
sudo systemctl enable virtualbox.service 2>/dev/null

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m========================================\033[0m"
echo -e "\033[1;32m✅ Установка VirtualBox завершена!\033[0m"
echo -e "\033[1;32m========================================\033[0m"
echo -e "\033[1;33m→ Для применения изменений рекомендуется перезагрузить систему\033[0m"
echo -e "\033[1;33m→ Гостевые дополнения (.iso) находятся в папке $DOWNLOAD_DIR\033[0m"

kdialog --title "Установка VirtualBox" \
        --msgbox "Установка VirtualBox завершена!\n\nДля применения изменений рекомендуется перезагрузить систему.\n\nГостевые дополнения (.iso) находятся в папке:\n$DOWNLOAD_DIR"
