#!/bin/bash

# check_state.sh - проверка реального состояния системы и установка флагов

STATE_DIR="$HOME/.config/alt-kde-helper/state.d"
mkdir -p "$STATE_DIR"

# Очистка всех старых флагов
rm -f "$STATE_DIR"/*

# ============================================================
# 1. Зеркала репозитория
# ============================================================

# Определяем текущее зеркало через apt-repo (без sudo)
CURRENT_REPO=$(apt-repo 2>/dev/null | head -1 | awk '{print $3}')

if echo "$CURRENT_REPO" | grep -qi "yandex"; then
    # Зеркало Yandex
    touch "$STATE_DIR/03_repo_yandex_action.sh"
elif echo "$CURRENT_REPO" | grep -qiE "ftp\.altlinux\.org|p11|altlinux"; then
    # Репозиторий по умолчанию p11 или altlinux.org
    touch "$STATE_DIR/04_repo_p11_action.sh"
else
    # Другое зеркало (скорее всего, самое быстрое)
    touch "$STATE_DIR/02_repo_fast_mirror_action.sh"
fi

# ============================================================
# 2. Установка eepm (06_install_eepm_action.sh)
# ============================================================

if rpm -q eepm epmgpi eepm-play-gui &>/dev/null; then
    touch "$STATE_DIR/06_install_eepm_action.sh"
fi

# ============================================================
# 3. Добавление пользователя в группы (08_add_groups_action.sh)
# ============================================================

USER_NAME="$USER"

# Проверяем группы dialout и lp
IN_DIALOUT=$(groups "$USER_NAME" | grep -q "dialout" && echo "yes" || echo "no")
IN_LP=$(groups "$USER_NAME" | grep -q "lp" && echo "yes" || echo "no")

if [ "$IN_DIALOUT" = "yes" ] && [ "$IN_LP" = "yes" ]; then
    # Проверяем группу adbusers (только если существует)
    if getent group adbusers >/dev/null 2>&1; then
        # Группа существует — проверяем, входит ли пользователь
        if groups "$USER_NAME" | grep -q "adbusers"; then
            touch "$STATE_DIR/08_add_groups_action.sh"
        fi
    else
        # Группы нет — ставим флаг
        touch "$STATE_DIR/08_add_groups_action.sh"
    fi
fi

# ============================================================
# 4. Установка flatpak (10_install_flatpak_action.sh)
# ============================================================

if rpm -q flatpak flatpak-repo-flathub firsttime-flatpak-mask-openh264 flatpak-kcm plasma-discover-flatpak &>/dev/null; then
    touch "$STATE_DIR/10_install_flatpak_action.sh"
fi

# ============================================================
# 5. Доступ flatpak к домашнему каталогу (11_flatpak_home_access_action.sh)
# ============================================================

if command -v flatpak &> /dev/null; then
    OVERRIDES=$(flatpak override --user --show 2>/dev/null)
    if echo "$OVERRIDES" | grep -qE "filesystems=home(:ro)?"; then
        touch "$STATE_DIR/11_flatpak_home_access_action.sh"
    fi
fi

# ============================================================
# 6. Исправление индикатора копирования (12_fix_copy_indicator_action.sh)
# ============================================================

if [ -f "/etc/sysctl.d/90-dirty.conf" ]; then
    touch "$STATE_DIR/12_fix_copy_indicator_action.sh"
fi

# ============================================================
# 7. Размер шрифта 10 (13_increase_fonts_action.sh)
# ============================================================

FONT_SIZE=$(kreadconfig6 --file kdeglobals --group General --key font 2>/dev/null | cut -d',' -f2)
if [ "$FONT_SIZE" = "10" ]; then
    touch "$STATE_DIR/13_increase_fonts_action.sh"
fi

# ============================================================
# 8. Миниатюры для 3D-файлов (14_thumbnails_3d_action.sh)
# ============================================================

if rpm -q f3d &>/dev/null && [ -f "/usr/local/bin/freecad-thumbnailer" ]; then
    touch "$STATE_DIR/14_thumbnails_3d_action.sh"
fi

# ============================================================
# 9. Миниатюры для DWG файлов (15_thumbnails_dwg_action.sh)
# ============================================================

if [ -f "/usr/local/bin/dwg-thumbnail.sh" ] && [ -f "/usr/share/thumbnailers/dwg.thumbnailer" ]; then
    touch "$STATE_DIR/15_thumbnails_dwg_action.sh"
fi

# ============================================================
# 10. 3D-ускорение для Google Chrome (16_flatpak_chrome_3d_action.sh)
# ============================================================

OVERRIDES=$(flatpak override --user --show com.google.Chrome 2>/dev/null)
if echo "$OVERRIDES" | grep -qE "socket=x11|socket=wayland|devices=dri"; then
    touch "$STATE_DIR/16_flatpak_chrome_3d_action.sh"
fi

# ============================================================
# 11. Разрешение загрузки тем и виджетов из сети (17_enable_ghns_action.sh)
# ============================================================

if grep -q "ghns=true" /etc/kf5/xdg/kdeglobals 2>/dev/null && \
   grep -q "ghns=true" /etc/xdg/kdeglobals 2>/dev/null; then
    touch "$STATE_DIR/17_enable_ghns_action.sh"
fi

# ============================================================
# 12. Установка значков papirus (18_install_papirus_icons_action.sh)
# ============================================================

if rpm -q papirus-remix-icon-theme &>/dev/null; then
    touch "$STATE_DIR/18_install_papirus_icons_action.sh"
fi

# ============================================================
# 13. Установка stplr (20_install_stplr_action.sh)
# ============================================================

if rpm -q stplr stplr-repo-aides plasma-discover-stplr &>/dev/null; then
    touch "$STATE_DIR/20_install_stplr_action.sh"
fi

# ============================================================
# 14. Установка кодека openh264 для Flatpak (21_install_openh264_action.sh)
# ============================================================

if flatpak list | grep -q "org.freedesktop.Platform.openh264"; then
    touch "$STATE_DIR/21_install_openh264_action.sh"
fi

# ============================================================
# 15. Обновление системы (05_update_system_action.sh)
# ============================================================
# Флаг остаётся как есть — реальную проверку сделать невозможно

# ============================================================
# 16. Очистка кэша (95_clean_cache_action.sh)
# ============================================================
# Флаг остаётся как есть — реальную проверку сделать невозможно

echo -e "\033[1;32m✅ Состояние системы проверено, флаги обновлены\033[0m"
