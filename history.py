# Модуль персистентной истории — сохраняет и загружает диалог в JSON
import json
import os

# Путь к файлу истории (рядом с модулем)
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "chat_history.json")


def load_history() -> list:
    """Загружает список сообщений из файла. При ошибке возвращает пустой список."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def save_history(messages: list) -> None:
    """Сохраняет список сообщений в JSON с отступами для читаемости."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as fh:
            json.dump(messages, fh, ensure_ascii=False, indent=2)
    except IOError as exc:
        print(f"[history] Не удалось сохранить историю: {exc}")


def clear_history() -> None:
    """Удаляет файл истории, если он существует."""
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
