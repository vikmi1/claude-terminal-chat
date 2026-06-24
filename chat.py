# Модуль чата — взаимодействие с Anthropic API
import os
import anthropic

from rich.live import Live
from rich.console import Group
from rich.text import Text
from rich.panel import Panel
from display import create_spinner, console

# Системный промпт для ассистента
SYSTEM_PROMPT = "Вы полезный ассистент, отвечайте на русском языке"

# Модель по умолчанию
MODEL = "claude-opus-4-8"

# Лимит токенов для обычного режима
MAX_TOKENS = 2000

# Лимит для режимов с размышлениями — thinking-блоки тоже расходуют токены из этого лимита,
# поэтому нужен значительно больший запас, иначе adaptive thinking отключается
MAX_TOKENS_THINKING = 5000


# Короткие описания для известных моделей
_MODEL_NOTES: dict[str, str] = {
    "claude-opus-4-8":           "самый мощный · thinking",
    "claude-opus-4-7":           "мощный · thinking",
    "claude-opus-4-6":           "мощный · thinking",
    "claude-sonnet-4-6":         "сбалансированный · thinking",
    "claude-haiku-4-5-20251001": "быстрый · экономичный",
    "claude-haiku-4-5":          "быстрый · экономичный",
}


def get_available_models(client: anthropic.Anthropic) -> list[dict]:
    """
    Получает список моделей через API Anthropic.
    При ошибке возвращает встроенный резервный список.
    """
    _FALLBACK = [
        {"id": "claude-opus-4-8",          "name": "Claude Opus 4.8",   "note": _MODEL_NOTES["claude-opus-4-8"]},
        {"id": "claude-sonnet-4-6",         "name": "Claude Sonnet 4.6", "note": _MODEL_NOTES["claude-sonnet-4-6"]},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5",  "note": _MODEL_NOTES["claude-haiku-4-5-20251001"]},
    ]
    try:
        page = client.models.list()
        models = []
        for m in page.data:
            if m.id == "claude-fable-5":
                continue
            name = getattr(m, "display_name", m.id)
            note = _MODEL_NOTES.get(m.id, "")
            models.append({"id": m.id, "name": name, "note": note})
        return models if models else _FALLBACK
    except Exception:
        return _FALLBACK


def create_client() -> anthropic.Anthropic:
    """Создаёт и возвращает клиент Anthropic API из переменной окружения."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY не найден. Добавьте его в файл .env"
        )
    return anthropic.Anthropic(api_key=api_key)


def _content_to_dicts(blocks) -> list:
    """
    Конвертирует Pydantic-блоки ответа API в простые словари для хранения.
    Поле signature сохраняется для корректного replay при следующих запросах.
    """
    result = []
    for block in blocks:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "thinking":
            entry: dict = {"type": "thinking", "thinking": block.thinking}
            # signature необходим для верификации на стороне API
            if getattr(block, "signature", None):
                entry["signature"] = block.signature
            result.append(entry)
    return result


def _prepare_messages_for_api(messages: list, thinking_mode: bool) -> list:
    """
    В обычном режиме удаляет thinking-блоки из истории перед отправкой,
    так как API в режиме disabled их не принимает.
    """
    if thinking_mode:
        return messages

    prepared = []
    for msg in messages:
        content = msg["content"]
        if isinstance(content, list):
            # Оставляем только text-блоки
            text_blocks = [b for b in content if b.get("type") == "text"]
            if not text_blocks:
                continue
            # Упрощаем до строки если один блок
            if len(text_blocks) == 1:
                prepared.append({"role": msg["role"], "content": text_blocks[0]["text"]})
            else:
                prepared.append({"role": msg["role"], "content": text_blocks})
        else:
            prepared.append(msg)
    return prepared


def generate_response(
    client: anthropic.Anthropic,
    messages: list,
    thinking_mode: bool = True,
    model: str = MODEL,
) -> tuple[str, str, list]:
    """
    Отправляет историю сообщений в API и возвращает ответ.

    Возвращает кортеж:
        response_text  — текст ответа ассистента
        thinking_text  — текст размышлений (пустая строка если режим отключён)
        messages       — обновлённая история со свежим ответом ассистента
    """
    api_messages = _prepare_messages_for_api(messages, thinking_mode)

    request_params: dict = {
        "model": model,
        "max_tokens": MAX_TOKENS_THINKING if thinking_mode else MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": api_messages,
        "thinking": {"type": "adaptive"} if thinking_mode else {"type": "disabled"},
    }

    thinking_text = ""
    response_text = ""

    # Стриминг с визуальным индикатором загрузки
    with create_spinner("Думаю..."):
        with client.messages.stream(**request_params) as stream:
            final_message = stream.get_final_message()

    # Извлекаем текст и размышления из блоков ответа
    for block in final_message.content:
        if block.type == "thinking":
            thinking_text = block.thinking
        elif block.type == "text":
            response_text = block.text

    # Записываем ответ ассистента в историю (сохраняем thinking-блоки для replay)
    messages.append({
        "role": "assistant",
        "content": _content_to_dicts(final_message.content),
    })

    usage = {
        "input": final_message.usage.input_tokens,
        "output": final_message.usage.output_tokens,
    }
    return response_text, thinking_text, messages, usage


def stream_response(
    client: anthropic.Anthropic,
    messages: list,
    model: str = MODEL,
) -> tuple[str, str, list]:
    """
    Режим 3: потоковый вывод размышлений и ответа в реальном времени.
    Использует Rich Live для обновления панелей прямо во время генерации.
    """
    request_params: dict = {
        "model": model,
        "max_tokens": MAX_TOKENS_THINKING,
        "system": SYSTEM_PROMPT,
        "messages": messages,
        "thinking": {"type": "adaptive"},
    }

    thinking_parts: list[str] = []
    text_parts: list[str] = []
    current_block_type: str = ""
    thinking_finished = False

    def make_renderable():
        """Собирает текущее состояние для Live-дисплея."""
        renderables = []

        if thinking_parts:
            t_title = (
                "[yellow]Размышления ИИ ✓[/yellow]"
                if thinking_finished
                else "[dim yellow]Размышления ИИ...[/dim yellow]"
            )
            renderables.append(
                Panel(
                    Text("".join(thinking_parts)),
                    title=t_title,
                    border_style="yellow",
                    padding=(0, 1),
                )
            )

        if text_parts:
            renderables.append(
                Panel(
                    Text("".join(text_parts)),
                    title="[green]Ассистент...[/green]",
                    border_style="green",
                    padding=(0, 1),
                )
            )

        if not renderables:
            return Text("⏳ Подключаюсь...", style="dim")

        return Group(*renderables)

    with Live(make_renderable(), console=console, refresh_per_second=12) as live:
        with client.messages.stream(**request_params) as stream:
            for event in stream:
                # Начало нового блока контента
                if event.type == "content_block_start":
                    current_block_type = event.content_block.type
                    # Фиксируем завершение размышлений при переходе к тексту
                    if current_block_type == "text" and thinking_parts:
                        thinking_finished = True
                        live.update(make_renderable())

                # Дельта контента — обновляем накопленные буферы
                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "thinking_delta" and delta.thinking:
                        thinking_parts.append(delta.thinking)
                        live.update(make_renderable())
                    elif delta.type == "text_delta" and delta.text:
                        text_parts.append(delta.text)
                        live.update(make_renderable())

            final_message = stream.get_final_message()

    thinking_text = "".join(thinking_parts)
    response_text = "".join(text_parts)

    # Сохраняем ответ в историю (с thinking-блоками для replay)
    messages.append({
        "role": "assistant",
        "content": _content_to_dicts(final_message.content),
    })

    usage = {
        "input": final_message.usage.input_tokens,
        "output": final_message.usage.output_tokens,
    }
    return response_text, thinking_text, messages, usage


def summarize_history(
    client: anthropic.Anthropic,
    messages: list,
    model: str = MODEL,
) -> tuple[list, int]:
    """
    Сжимает историю диалога: отправляет все сообщения в API,
    получает краткое резюме и заменяет им всю историю.
    Возвращает (сжатые_сообщения, количество_исходных_сообщений).
    """
    if len(messages) < 2:
        return messages, 0

    # Собираем читаемый текст истории (только text-блоки, без thinking)
    lines = []
    for msg in messages:
        role_label = "Пользователь" if msg["role"] == "user" else "Ассистент"
        content = msg["content"]
        if isinstance(content, str):
            text = content
        else:
            text = " ".join(
                b.get("text", "") for b in content if b.get("type") == "text"
            )
        if text.strip():
            lines.append(f"{role_label}: {text.strip()}")

    history_text = "\n\n".join(lines)

    with create_spinner("Суммаризирую историю..."):
        response = client.messages.create(
            model=model,
            max_tokens=800,
            system="Ты ассистент для суммаризации диалогов. Отвечай только на русском.",
            messages=[{
                "role": "user",
                "content": (
                    "Напиши краткое резюме следующего диалога. "
                    "Сохрани ключевые темы, факты и договорённости "
                    "так, чтобы можно было продолжить разговор с этим контекстом.\n\n"
                    + history_text
                ),
            }],
            thinking={"type": "disabled"},
        )

    summary_text = response.content[0].text
    original_count = len(messages)

    # Два сообщения вместо всей истории
    compressed = [
        {
            "role": "user",
            "content": "Ниже — краткое резюме нашего предыдущего разговора.",
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": summary_text}],
        },
    ]

    return compressed, original_count
