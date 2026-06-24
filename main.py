# Точка входа — выбор режима/модели, основной цикл диалога, выход с историей
from dotenv import load_dotenv

from display import (
    console,
    show_welcome,
    show_commands_hint,
    show_thinking,
    show_assistant_message,
    show_token_usage,
    show_history,
    show_error,
    show_info,
)
from history import load_history, save_history, clear_history
from chat import create_client, get_available_models, generate_response, stream_response, summarize_history


def _select_mode() -> int:
    """
    Запрашивает режим работы.
    Возвращает 1 (Thinking), 2 (Обычный) или 3 (Прямая трансляция).
    """
    console.print("\n[bold]Выберите режим работы:[/bold]")
    console.print("  [bold cyan]1[/bold cyan] — Thinking        [dim]— размышления показываются после ответа (по умолчанию)[/dim]")
    console.print("  [bold yellow]2[/bold yellow] — Обычный         [dim]— без размышлений[/dim]")
    console.print("  [bold magenta]3[/bold magenta] — Прямая трансляция [dim]— видите, как модель думает прямо сейчас[/dim]\n")

    try:
        choice = input("Ваш выбор (Enter = 1): ").strip()
    except (KeyboardInterrupt, EOFError):
        return 1

    if choice == "2":
        return 2
    if choice == "3":
        return 3
    return 1


def _select_model(client) -> tuple[str, str]:
    """
    Показывает список доступных моделей из API.
    Возвращает (model_id, display_name).
    """
    models = get_available_models(client)

    console.print("\n[bold]Выберите модель:[/bold]")
    for i, m in enumerate(models, 1):
        note = f"  [dim]{m['note']}[/dim]" if m.get("note") else ""
        console.print(f"  [bold cyan]{i}[/bold cyan] — {m['name']}{note}")
    console.print()

    default_name = models[0]["name"]
    try:
        choice = input(f"Ваш выбор (Enter = 1 — {default_name}): ").strip()
    except (KeyboardInterrupt, EOFError):
        return models[0]["id"], models[0]["name"]

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx]["id"], models[idx]["name"]
    except (ValueError, IndexError):
        pass

    return models[0]["id"], models[0]["name"]


def configure_session(client) -> tuple[int, str, str]:
    """
    Последовательно запрашивает режим и модель.
    Возвращает (mode, model_id, model_name).
    """
    mode = _select_mode()
    model_id, model_name = _select_model(client)
    return mode, model_id, model_name


def main() -> None:
    """Главная функция приложения."""
    load_dotenv()

    # Клиент создаётся до меню — нужен для получения списка моделей
    try:
        client = create_client()
    except ValueError as exc:
        show_error(str(exc))
        return

    mode, model_id, model_name = configure_session(client)
    show_welcome(mode, model_name)
    show_commands_hint()

    messages = load_history()
    if messages:
        show_info(f"Загружено {len(messages)} сообщений из предыдущего сеанса")

    session_tokens = 0  # накопленный счётчик токенов за сессию

    while True:
        try:
            user_input = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "exit"

        if not user_input:
            continue

        # --- Команды управления ---
        if user_input.lower() == "exit":
            save_history(messages)
            show_info("История сохранена. До свидания!")
            break

        if user_input.lower() == "clear":
            messages = []
            clear_history()
            show_info("История диалога очищена")
            continue

        if user_input.lower() == "help":
            show_commands_hint()
            continue

        if user_input.lower() == "summarize":
            if len(messages) < 2:
                show_info("История слишком короткая — нечего сжимать")
                continue
            before = len(messages)
            try:
                messages, _ = summarize_history(client, messages, model_id)
                save_history(messages)
                show_info(f"История сжата: {before} сообщений → {len(messages)} (резюме)")
                show_assistant_message(messages[1]["content"][0]["text"])
            except Exception as exc:  # noqa: BLE001
                show_error(f"Ошибка суммаризации: {exc}")
            continue

        if user_input.lower() == "mode":
            mode, model_id, model_name = configure_session(client)
            show_welcome(mode, model_name)
            show_commands_hint()
            continue

        # --- Отправляем сообщение ---
        messages.append({"role": "user", "content": user_input})

        try:
            if mode == 3:
                # Режим прямой трансляции — вывод управляется внутри stream_response
                response_text, thinking_text, messages, usage = stream_response(
                    client, messages, model_id
                )
            else:
                response_text, thinking_text, messages, usage = generate_response(
                    client, messages, mode == 1, model_id
                )
                if mode == 1 and thinking_text:
                    show_thinking(thinking_text)
                show_assistant_message(response_text)

        except Exception as exc:  # noqa: BLE001
            show_error(f"Ошибка API: {exc}")
            messages.pop()
            continue

        request_tokens = usage["input"] + usage["output"]
        session_tokens += request_tokens
        show_token_usage(request_tokens, session_tokens)

        save_history(messages)


if __name__ == "__main__":
    main()
