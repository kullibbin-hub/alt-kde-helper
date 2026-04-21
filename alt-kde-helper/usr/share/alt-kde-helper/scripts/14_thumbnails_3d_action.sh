#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mПоказ миниатюр для 3D-файлов (STL, FCstd)\033[0m"
echo -e "\033[1;36m========================================\033[0m"

echo -e "\033[1;33m→ Обновление списка пакетов...\033[0m"
sudo apt-get update
if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось обновить список пакетов\033[0m"
    exit 1
fi

# Проверка и установка f3d
if ! command -v f3d &> /dev/null; then
    echo -e "\033[1;33m→ f3d не установлен. Поиск в репозитории...\033[0m"

    if apt-cache show f3d &> /dev/null; then
        echo -e "\033[1;33m→ f3d найден в репозитории. Установка...\033[0m"
        sudo apt-get install -y f3d
        if [ $? -ne 0 ]; then
            echo -e "\033[1;31m❌ Ошибка: не удалось установить f3d из репозитория\033[0m"
            exit 1
        fi
    else
        echo -e "\033[1;33m→ f3d не найден в репозитории. Установка через eepm...\033[0m"

        if ! command -v epm &> /dev/null; then
            echo -e "\033[1;33m→ eepm не установлен. Установка...\033[0m"
            sudo apt-get install -y eepm
            if [ $? -ne 0 ]; then
                echo -e "\033[1;31m❌ Ошибка: не удалось установить eepm\033[0m"
                exit 1
            fi
        else
            echo -e "\033[1;32m✓ eepm уже установлен\033[0m"
        fi

        echo -e "\033[1;33m→ Установка f3d через epm play...\033[0m"
        sudo epm play -y f3d
        if [ $? -ne 0 ]; then
            echo -e "\033[1;31m❌ Ошибка: не удалось установить f3d через epm\033[0m"
            exit 1
        fi
    fi
else
    echo -e "\033[1;32m✓ f3d уже установлен\033[0m"
fi

echo -e "\033[1;33m→ Создание thumbnailer для .FCstd файлов...\033[0m"

echo -e "\033[1;33m→ Создание файла /usr/local/bin/freecad-thumbnailer...\033[0m"
sudo tee /usr/local/bin/freecad-thumbnailer > /dev/null << 'EOF'
#!/bin/bash

INPUT="$3"
OUTPUT="$4"

# проверка наличия thumbnail внутри архива
if unzip -l "$INPUT" thumbnails/Thumbnail.png >/dev/null 2>&1; then
    unzip -p "$INPUT" thumbnails/Thumbnail.png > "$OUTPUT"
    exit 0
else
    # важно: не создавать OUTPUT
    exit 1
fi
EOF

sudo chmod +x /usr/local/bin/freecad-thumbnailer

echo -e "\033[1;33m→ Создание файла /usr/share/thumbnailers/FreeCAD1.thumbnailer...\033[0m"
sudo tee /usr/share/thumbnailers/FreeCAD1.thumbnailer > /dev/null << 'EOF'
[Thumbnailer Entry]
TryExec=freecad-thumbnailer
Exec=freecad-thumbnailer -s %s %i %o
MimeType=application/x-extension-fcstd;
EOF

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Миниатюры для 3D-файлов настроены\033[0m"
