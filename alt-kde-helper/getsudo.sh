#!/bin/bash
set -e

REAL_USER="$1"

# Установка sudo при необходимости
if ! command -v sudo &>/dev/null; then
    apt-get update || true
    apt-get install -y sudo || true
fi

control sudowheel enabled || true
usermod -aG wheel "$REAL_USER" || true
