#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОбновление / удаление ядер\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Запрос подтверждения через kdialog
kdialog --title "Обновление ядра" \
        --yesno "Внимание! Сейчас будет выполнено обновление ядра.\n\nВнимательно следите за выводом в терминале.\n\nПосле установки выбранного ядра, можно будет удалить старые неиспользуемые ядра, согласившись явно на вопрос об удалении.\n\nТекущее и свежеустановленные ядра удалены не будут.\n\nВ случае проблем при загрузке с новым ядром — всегда можно выбрать предыдущее ядро в меню загрузчика (Grub) при включении компьютера (второй пункт).\n\nПродолжить?"
if [ $? -ne 0 ]; then
    echo -e "\033[1;33m⚠ Обновление ядра отменено пользователем\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

echo -e "\033[1;33m→ Обновление списков пакетов (apt)...\033[0m"
sudo apt-get update
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить списки пакетов\033[0m"
    exit 1
fi

# Текущее ядро
CURRENT_KERNEL=$(uname -r)
CURRENT_VERSION=$(echo "$CURRENT_KERNEL" | cut -d'-' -f1)
echo -e "\033[1;36mТекущее ядро: $CURRENT_KERNEL\033[0m"

# По умолчанию «новое ядро» = текущее. Если пользователь установит новое — переопределим.
SELECTED_VERSION="$CURRENT_VERSION"
SELECTED_SHORT=""
SELECTED_KERNEL=""

# Все длинные имена ядер, известные APT
echo -e "\033[1;33m→ Поиск доступных ядер...\033[0m"
LONG_NAMES=()
SHORT_NAMES=()
STATUS=()
while read -r long; do
    left="${long%%#*}"
    rest="${long#*#}"
    ver="${rest%%:*}"
    short="${left}-${ver}"
    short_version=$(echo "$short" | sed 's/^kernel-image-[0-9.]*-\([0-9.]*\)-.*/\1/')
    if [ "$short_version" != "$CURRENT_VERSION" ]; then
        # Определяем статус: установлено или доступно
        if rpm -qa | grep -q "^${short}\.x86_64$"; then
            STATUS+=("установлено")
        else
            STATUS+=("доступно для загрузки")
        fi
        LONG_NAMES+=("$long")
        SHORT_NAMES+=("$short")
    fi
done < <(apt-cache pkgnames | grep '^kernel-image-[0-9]' | grep '#' | sort -V)

if [ ${#LONG_NAMES[@]} -eq 0 ]; then
    echo -e "\033[1;33m⚠ Новых версий ядра нет\033[0m"
else
    # Показываем список
    echo -e "\033[1;36mДоступные ядра для установки:\033[0m"
    echo ""
    for i in "${!SHORT_NAMES[@]}"; do
        printf "%3d) %s - %s\n" "$((i+1))" "${SHORT_NAMES[$i]}" "${STATUS[$i]}"
    done
    TOTAL_COUNT=${#LONG_NAMES[@]}
    printf "%3d) %s\n" 0 "Не устанавливать новое ядро"
    echo ""

    # Выбор
    while true; do
        read -r -p "Выберите номер ядра для установки (0-$TOTAL_COUNT): " CHOICE

        if [ -z "$CHOICE" ]; then
            echo -e "\033[1;31m❌ Ввод некорректный. Попробуйте снова.\033[0m"
            continue
        fi

        if ! [[ "$CHOICE" =~ ^[0-9]+$ ]]; then
            echo -e "\033[1;31m❌ Ввод некорректный. Введите число.\033[0m"
            continue
        fi

        if [ "$CHOICE" -gt "$TOTAL_COUNT" ]; then
            echo -e "\033[1;31m❌ Ввод некорректный. Номер должен быть от 0 до $TOTAL_COUNT.\033[0m"
            continue
        fi

        break
    done

    if [ "$CHOICE" != "0" ]; then
        IDX=$((CHOICE-1))
        SELECTED_KERNEL="${LONG_NAMES[$IDX]}"
        SELECTED_SHORT="${SHORT_NAMES[$IDX]}"

        # Dry-run
        echo -e "\033[1;33m→ Проверка ядра: $SELECTED_SHORT\033[0m"
        echo ""

        DRY_RUN_OUTPUT=$(echo "n" | sudo update-kernel -n --fw -r "$SELECTED_KERNEL" 2>&1)
        echo "$DRY_RUN_OUTPUT"
        echo ""

        if echo "$DRY_RUN_OUTPUT" | grep -q "ATTENTION: Selected kernel does not have"; then
            echo -e "\033[1;31m❌ Для выбранного ядра не хватает нужных модулей (драйверов).\033[0m"
            echo -e "\033[1;31m   Установка отменена.\033[0m"
            rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
            exit 0
        fi

        echo -e "\033[1;32m✅ Установка возможна.\033[0m"

        while true; do
            read -r -p "Установить ядро $SELECTED_SHORT? [Y/n]: " INSTALL_CHOICE
            if [ -z "$INSTALL_CHOICE" ] || [[ "$INSTALL_CHOICE" =~ ^[YyДд]$ ]]; then
                break
            elif [[ "$INSTALL_CHOICE" =~ ^[NnНн]$ ]]; then
                # Отказ от установки. Идём в блок удаления старых.
                SELECTED_KERNEL=""
                SELECTED_SHORT=""
                break
            else
                echo -e "\033[1;31m❌ Ввод некорректный. Введите Y или N.\033[0m"
            fi
        done

        if [ -n "$SELECTED_KERNEL" ]; then
            echo -e "\033[1;32m→ Устанавливается ядро: $SELECTED_SHORT\033[0m"
            echo ""

            yes | sudo update-kernel --fw -r "$SELECTED_KERNEL"
            EXIT_CODE=${PIPESTATUS[1]}

            if [ $EXIT_CODE -ne 0 ]; then
                echo -e "\033[1;31m❌ Ошибка при установке ядра\033[0m"
                kdialog --title "Обновление ядра" \
                        --error "Произошла ошибка при установке ядра.\n\nПодробности смотрите в терминале."
                exit 1
            fi

            # Переключаем загрузку по умолчанию на выбранное ядро
            left="${SELECTED_KERNEL%%#*}"
            rest="${SELECTED_KERNEL#*#}"
            ver="${rest%%:*}"
            flavour="${left#kernel-image-}"
            version="${ver%-alt*}"
            release="${ver##*-}"
            installkernel_arg="${version}-${flavour}-${release}"

            echo -e "\033[1;32m→ Переключение загрузки по умолчанию на $installkernel_arg\033[0m"
            echo ""

            sudo installkernel "$installkernel_arg"
            if [ $? -ne 0 ]; then
                echo -e "\033[1;31m❌ Ошибка при переключении загрузки по умолчанию\033[0m"
                kdialog --title "Обновление ядра" \
                        --error "Ядро установлено, но не удалось переключить загрузку по умолчанию.\n\nПодробности смотрите в терминале."
                exit 1
            fi

            echo -e "\033[1;32m✅ Ядро установлено, загрузка по умолчанию переключена\033[0m"

            # Версия нового ядра для блока удаления
            SELECTED_VERSION="$version"
        fi
    fi
fi

# Установленные короткие имена
INSTALLED_SHORT=$(rpm -qa | grep '^kernel-image-[0-9]' | sed 's/\.x86_64$//')

# Формируем список на удаление
KERNELS_TO_REMOVE=()
while read -r pkg; do
    pkg_version=$(echo "$pkg" | sed 's/^kernel-image-[0-9.]*-\([0-9.]*\)-.*/\1/')
    if [ "$pkg_version" != "$CURRENT_VERSION" ] && [ "$pkg_version" != "$SELECTED_VERSION" ]; then
        KERNELS_TO_REMOVE+=("$pkg")
    fi
done < <(echo "$INSTALLED_SHORT")

if [ ${#KERNELS_TO_REMOVE[@]} -gt 0 ]; then
    echo -e "\033[1;36m\nВ системе обнаружены старые ядра:\033[0m"
    echo -e "\033[1;32mТекущее ядро: $CURRENT_KERNEL\033[0m"
    if [ -n "$SELECTED_SHORT" ]; then
        echo -e "\033[1;32mНовое ядро: $SELECTED_SHORT\033[0m"
    fi
    echo -e "\033[1;33mЯдра на удаление:\033[0m"
    for pkg in "${KERNELS_TO_REMOVE[@]}"; do
        echo "  $pkg"
    done
    echo ""

    while true; do
        read -r -p "Удалить старые ядра? [y/N]: " REMOVE_CHOICE

        if [[ "$REMOVE_CHOICE" =~ ^[YyДд]$ ]]; then
            echo -e "\033[1;33m→ Удаление старых ядер...\033[0m"
            for pkg in "${KERNELS_TO_REMOVE[@]}"; do
                long=""
                for l in "${LONG_NAMES[@]}"; do
                    left="${l%%#*}"
                    rest="${l#*#}"
                    ver="${rest%%:*}"
                    s="${left}-${ver}"
                    if [ "$s" = "$pkg" ]; then
                        long="$l"
                        break
                    fi
                done
                if [ -n "$long" ]; then
                    echo "Удаляется: $pkg"
                    sudo apt-get remove -y "$long"
                else
                    echo -e "\033[1;33m⚠ Не найдено длинное имя для $pkg, пропуск\033[0m"
                fi
            done
            echo -e "\033[1;32m✅ Старые ядра удалены\033[0m"
            break
        elif [ -z "$REMOVE_CHOICE" ] || [[ "$REMOVE_CHOICE" =~ ^[NnНн]$ ]]; then
            echo -e "\033[1;33m⚠ Удаление старых ядер отменено\033[0m"
            break
        else
            echo -e "\033[1;31m❌ Ввод некорректный. Введите Y или N.\033[0m"
        fi
    done
else
    echo -e "\033[1;33m⚠ Старых ядер для удаления нет\033[0m"
fi

if [ -n "$SELECTED_SHORT" ]; then
    echo ""
    echo -e "\033[1;33m→ Для применения нового ядра требуется перезагрузка\033[0m"
fi
rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
