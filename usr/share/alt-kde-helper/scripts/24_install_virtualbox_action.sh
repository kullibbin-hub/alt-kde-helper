#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mУстановка VirtualBox и дополнений\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# ============================================================
# ШАГ 1: Проверяем flavour ядра, пишем в echo
# ============================================================
CURRENT_KERNEL_FLAVOUR=$(uname -r | cut -d '.' -f1,2)
echo -e "\033[1;33m→ Текущий flavour ядра: $CURRENT_KERNEL_FLAVOUR\033[0m"

# ============================================================
# ШАГ 2: Обновление кэша apt-get update, с проверкой на ошибку
# ============================================================
echo -e "\033[1;33m→ Обновление базы данных пакетов...\033[0m"
if ! sudo apt-get update; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить кэш APT\033[0m"
    kdialog --title "Ошибка" --error "Не удалось обновить базу данных пакетов. Проверьте подключение к интернету."
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 1
fi

# ============================================================
# ШАГ 3: Проверяем наличие epm, устанавливаем если нет
# ============================================================
if ! command -v epm &>/dev/null; then
    echo -e "\033[1;33m→ Утилита eepm не найдена. Установка...\033[0m"
    if ! sudo apt-get install -y eepm; then
        echo -e "\033[1;31m❌ Ошибка: не удалось установить eepm\033[0m"
        kdialog --title "Ошибка" --error "Не удалось установить eepm."
        rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
        exit 1
    fi
    echo -e "\033[1;32m✓ eepm успешно установлен.\033[0m"
fi

# ============================================================
# ШАГ 4: Установка VirtualBox через epm play (без проверки на ошибку)
# ============================================================
echo -e "\033[1;33m→ Установка VirtualBox через epm...\033[0m"
epm play -y virtualbox

# ============================================================
# ШАГ 5: Проверяем наличие пакета модуля для текущей или будущей версии ядра
# ============================================================
if ! rpm -qa | grep "kernel-modules-virtualbox-" | grep -E "kernel-modules-virtualbox-.*($CURRENT_KERNEL_FLAVOUR|[0-9]+\.[0-9]+)" | sort -V | tail -1 | grep -q "$CURRENT_KERNEL_FLAVOUR"; then
    echo -e "\033[1;31m❌ Модуль VirtualBox для ядра flavour $CURRENT_KERNEL_FLAVOUR или новее не установлен\033[0m"
    kdialog --title "Ошибка установки модуля VirtualBox" \
            --error "Модуль VirtualBox для ядра flavour $CURRENT_KERNEL_FLAVOUR или новее не установлен.\n\nВозможно, в репозитории нет модуля для вашего ядра.\n\nПопробуйте загрузиться с предыдущим ядром (выбрать в меню Grub) и повторить установку."
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 1
fi
echo -e "\033[1;32m✓ Модуль VirtualBox для ядра flavour $CURRENT_KERNEL_FLAVOUR или новее установлен\033[0m"

# ============================================================
# Дополнительно: Добавление пользователя в группу vboxusers
# ============================================================
echo -e "\033[1;33m→ Добавление пользователя в группу vboxusers...\033[0m"
sudo usermod -aG vboxusers "$(whoami)"
echo -e "\033[1;32m✓ Пользователь добавлен в группу vboxusers\033[0m"

# ============================================================
# Отключение KVM через чёрный список
# ============================================================
echo -e "\033[1;33m→ Отключение поддержки KVM...\033[0m"
if lsmod | grep -q kvm_intel; then
    KVM_MODULE="kvm_intel"
elif lsmod | grep -q kvm_amd; then
    KVM_MODULE="kvm_amd"
else
    KVM_MODULE=""
fi

if [ -n "$KVM_MODULE" ]; then
    echo "blacklist $KVM_MODULE" | sudo tee /etc/modprobe.d/blacklist-kvm-for-virtualbox.conf > /dev/null
    echo -e "\033[1;32m✓ Модуль $KVM_MODULE добавлен в чёрный список\033[0m"
    sudo rmmod "$KVM_MODULE" 2>/dev/null
    echo -e "\033[1;32m✓ Модуль $KVM_MODULE выгружен\033[0m"
else
    echo -e "\033[1;33m→ KVM не обнаружен\033[0m"
fi

# ============================================================
# ШАГ 6: Установка Extension Pack через epm
# ============================================================
kdialog --title "Лицензионное соглашение Oracle Extension Pack" \
        --warningcontinuecancel "Oracle VM VirtualBox Extension Pack распространяется под проприетарной лицензией PUEL.\n\nБесплатно для личного и образовательного некоммерческого использования.\n\nПодробнее: https://www.virtualbox.org/wiki/ExtensionPack\n\nПродолжить установку?"

if [ $? -eq 0 ]; then
    echo -e "\033[1;33m→ Установка Extension Pack через epm...\033[0m"
    if ! epm play -y virtualbox-extpack; then
        echo -e "\033[1;31m❌ Ошибка при установке Extension Pack\033[0m"
        kdialog --title "Ошибка" --error "Не удалось установить Extension Pack."
        rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
        exit 1
    fi
    echo -e "\033[1;32m✓ Extension Pack установлен\033[0m"
else
    echo -e "\033[1;33m⚠ Установка Extension Pack отменена пользователем\033[0m"
fi

# ============================================================
# Скачивание Guest Additions ISO
# ============================================================
DOWNLOAD_DIR=$(xdg-user-dir DOWNLOAD 2>/dev/null)
if [ -z "$DOWNLOAD_DIR" ] || [ ! -d "$DOWNLOAD_DIR" ]; then
    DOWNLOAD_DIR="$HOME/Загрузки"
fi

VB_VERSION=$(vboxmanage --version 2>/dev/null | cut -d'r' -f1)
if [ -z "$VB_VERSION" ]; then
    VB_VERSION=$(rpm -q virtualbox --queryformat "%{VERSION}" 2>/dev/null | cut -d'-' -f1)
fi

if [ -n "$VB_VERSION" ]; then
    GUEST_ADDITIONS_URL="https://download.virtualbox.org/virtualbox/$VB_VERSION/VBoxGuestAdditions_$VB_VERSION.iso"
    GUEST_ADDITIONS_FILE="$DOWNLOAD_DIR/VBoxGuestAdditions_$VB_VERSION.iso"

    echo -e "\033[1;33m→ Скачивание гостевых дополнений...\033[0m"
    if [ -f "$GUEST_ADDITIONS_FILE" ]; then
        echo -e "\033[1;32m✓ Гостевые дополнения уже скачаны: $GUEST_ADDITIONS_FILE\033[0m"
    else
        if wget -q --show-progress -O "$GUEST_ADDITIONS_FILE" "$GUEST_ADDITIONS_URL"; then
            echo -e "\033[1;32m✓ Гостевые дополнения скачаны: $GUEST_ADDITIONS_FILE\033[0m"
        else
            echo -e "\033[1;33m⚠ Не удалось скачать гостевые дополнения\033[0m"
        fi
    fi
    echo -e "\033[1;33m→ Гостевые дополнения (.iso) сохранены в папку $DOWNLOAD_DIR\033[0m"
fi

# ============================================================
# Загрузка модуля ядра и запуск сервиса
# ============================================================
echo -e "\033[1;33m→ Загрузка модуля vboxdrv и запуск сервиса...\033[0m"
sudo modprobe vboxdrv 2>/dev/null
sudo systemctl restart virtualbox.service 2>/dev/null
sudo systemctl enable virtualbox.service 2>/dev/null

# ============================================================
# ШАГ 7: Успешное завершение
# ============================================================
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m========================================\033[0m"
echo -e "\033[1;32m✅ Установка VirtualBox завершена успешно!\033[0m"
echo -e "\033[1;32m========================================\033[0m"
echo -e "\033[1;33m→ Для применения изменений необходимо перезагрузить систему\033[0m"
echo -e "\033[1;33m→ Гостевые дополнения (.iso) находятся в папке $DOWNLOAD_DIR\033[0m"

kdialog --title "Установка VirtualBox" \
        --msgbox "Установка VirtualBox завершена успешно!\n\nДля применения изменений необходимо перезагрузить систему.\n\nГостевые дополнения (.iso) находятся в папке:\n$DOWNLOAD_DIR"
