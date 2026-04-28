#!/bin/bash
# check_sudo.sh - настройка sudo для текущего пользователя
# Запускается через pkexec

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null)}"

if [ -z "$REAL_USER" ]; then
    echo "Не удалось определить имя пользователя"
    exit 1
fi

# Настройка sudo (как в install.sh)
control sudowheel enabled || true
usermod -aG wheel "$REAL_USER" 2>/dev/null || true

echo "sudo настроен для пользователя $REAL_USER"
exit 0
