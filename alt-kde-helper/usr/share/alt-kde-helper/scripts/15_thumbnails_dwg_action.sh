#!/bin/bash

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mПоказ миниатюр для файлов .dwg (AutoCAD)\033[0m"
echo -e "\033[1;36m========================================\033[0m"

# Диалог с лицензией
kdialog --title "Лицензионное соглашение NConvert" \
        --warningcontinuecancel "NConvert бесплатен только для некоммерческого использования.\n\nПродолжить установку?"

if [ $? -ne 0 ]; then
    echo -e "\033[1;33m⚠ Пользователь отказался от установки\033[0m"
    rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"
    exit 0
fi

echo -e "\033[1;33m→ Скачивание NConvert...\033[0m"
cd /tmp
wget https://download.xnview.com/NConvert-linux64.tgz -O NConvert-linux64.tgz

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось скачать NConvert\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Распаковка NConvert...\033[0m"
sudo tar -xzf NConvert-linux64.tgz -C /usr/local

if [ $? -ne 0 ]; then
    echo -e "\033[1;31m❌ Ошибка: не удалось распаковать NConvert\033[0m"
    exit 1
fi

echo -e "\033[1;33m→ Создание симлинка...\033[0m"
sudo rm -f /usr/local/bin/nconvert
sudo ln -s /usr/local/NConvert/nconvert /usr/local/bin/nconvert

echo -e "\033[1;33m→ Создание dwg-thumbnail.sh...\033[0m"
sudo tee /usr/local/bin/dwg-thumbnail.sh >/dev/null <<'EOF'
#!/bin/bash
INPUT="$1"
OUTPUT="$2"
SIZE="$3"

NCONVERT="/usr/local/bin/nconvert"

# Создаём директорию для результата
mkdir -p "$(dirname "$OUTPUT")"

# Создаём временный файл с расширением .dwg
TMP="/tmp/dwgthumb-$$.dwg"
cp "$INPUT" "$TMP"

# Генерация PNG
"$NCONVERT" -quiet -out png -resize "$SIZE" "$SIZE" -o "$OUTPUT" "$TMP"

rm -f "$TMP"
EOF

sudo chmod +x /usr/local/bin/dwg-thumbnail.sh

echo -e "\033[1;33m→ Создание dwg.thumbnailer...\033[0m"
sudo tee /usr/share/thumbnailers/dwg.thumbnailer >/dev/null <<'EOF'
[Thumbnailer Entry]
TryExec=/usr/local/bin/dwg-thumbnail.sh
Exec=/usr/local/bin/dwg-thumbnail.sh %i %o %s
MimeType=image/vnd.dwg; image/x-dwg; application/acad;
Flags=NoCopy
EOF

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/$(basename "$0")"

rm -f "/tmp/alt-kde-helper-actions/$(basename "$0")"

echo -e "\033[1;32m✅ Миниатюры для DWG файлов настроены\033[0m"
