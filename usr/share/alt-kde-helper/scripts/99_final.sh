#!/bin/bash
# Финальный отчёт о выполнении действий

echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;36mОтчёт о выполнении действий\033[0m"
echo -e "\033[1;36m========================================\033[0m"

QUEUE_DIR="/tmp/alt-kde-helper-actions"

# Смотрим, какие скрипты остались в очереди (неудачные)
REMAINING=$(ls "$QUEUE_DIR" 2>/dev/null | grep -v "final.sh" | sort)

if [ -z "$REMAINING" ]; then
    echo -e "\033[1;32m✅ Все действия выполнены успешно!\033[0m"
else
    echo -e "\033[1;33m⚠ Следующие действия не выполнены (ошибки):\033[0m"
    echo ""
    for script in $REMAINING; do
        # Убираем _action.sh и _rollback.sh для читаемости
        name=$(echo "$script" | sed 's/_action\.sh$//' | sed 's/_rollback\.sh$//')
        echo -e "  \033[1;31m•\033[0m $name"
    done
    echo ""
    echo -e "\033[1;33mСовет: проверьте подключение к интернету и повторите попытку.\033[0m"

    # Удаляем все оставшиеся скрипты из очереди
    for script in $REMAINING; do
        rm -f "$QUEUE_DIR/$script"
    done
    echo -e "\033[1;32m🧹 Очередь очищена\033[0m"
fi

echo ""
echo -e "\033[1;36m========================================\033[0m"
echo -e "\033[1;33mНажмите любую клавишу для выхода...\033[0m"
read -n 1 -s
