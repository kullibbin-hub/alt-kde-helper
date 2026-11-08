# busy.py - глобальный счётчик занятости (konsole запущен)

import threading
from PyQt6.QtCore import QObject, pyqtSignal


class BusyState(QObject):
    """Глобальный счётчик активных konsole-сессий.

    Сигнал changed(True) эмитится при переходе 0 → 1,
    changed(False) — при 1 → 0. Промежуточные состояния не эмитятся:
    UI интересует только «занято / не занято».
    """

    changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._count = 0
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            was_idle = (self._count == 0)
            self._count += 1
        if was_idle:
            self.changed.emit(True)

    def release(self):
        with self._lock:
            if self._count == 0:
                return
            self._count -= 1
            became_idle = (self._count == 0)
        if became_idle:
            self.changed.emit(False)

    def is_busy(self):
        with self._lock:
            return self._count > 0


# Глобальный экземпляр — импортируется всеми модулями.
# Python кеширует модуль, поэтому BUSY везде один и тот же объект.
BUSY = BusyState()