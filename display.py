# Модуль отображения — красивый вывод в терминале через Rich
import sys

# Windows PowerShell/cmd по умолчанию использует cp1252 — принудительно UTF-8
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.rule import Rule
from rich.theme import Theme
from rich.live import Live
from rich.spinner import Spinner

# Цветовая схема
_theme = Theme({
    "user":      "bold cyan",
    "assistant": "bold green",
    "thinking":  "dim yellow",
    "info":      "dim white",
    "error":     "bold red",
})

console = Console(theme=_theme, legacy_windows=False)


def show_welcome(mode: int, model_name: str = "") -> None:
    """Приветственный экран с выбранным режимом и моделью."""
    _labels = {
        1: "[bold yellow]Thinking[/bold yellow] [dim](размышления — после ответа)[/dim]",
        2: "[bold white]Обычный[/bold white] [dim](без размышлений)[/dim]",
        3: "[bold magenta]Прямая трансляция[/bold magenta] [dim](размышления в реальном времени)[/dim]",
    }
    mode_label = _labels.get(mode, _labels[1])
    model_line = f"\nМодель:  [bold]{model_name}[/bold]" if model_name else ""
    console.print(Rule("AI Консоль", style="bold blue"))
    console.print(
        Panel(
            f"[bold]AI Чат готов к работе[/bold]\n\n"
            f"Режим:   {mode_label}{model_line}",
            title="[bold blue] AI Ассистент [/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()


def show_commands_hint() -> None:
    """Краткая подсказка по доступным командам."""
    console.print(
        Panel(
            "[bold]exit[/bold]       — завершить чат и сохранить историю\n"
            "[bold]clear[/bold]      — полностью очистить историю\n"
            "[bold]summarize[/bold]  — сжать историю через суммаризацию\n"
            "[bold]mode[/bold]       — сменить режим работы и модель\n"
            "[bold]help[/bold]       — показать эту подсказку",
            title="[info] Команды [/info]",
            border_style="dim",
            padding=(0, 2),
        )
    )
    console.print()


def show_user_message(text: str) -> None:
    """Панель сообщения пользователя."""
    console.print(
        Panel(text, title="[user] Вы [/user]", border_style="cyan", padding=(0, 1))
    )


def show_thinking(thinking_text: str) -> None:
    """Панель с блоком размышлений ИИ."""
    if not thinking_text:
        return
    console.print(
        Panel(
            thinking_text,
            title="[thinking] Размышления ИИ [/thinking]",
            subtitle="[dim]thinking[/dim]",
            border_style="yellow",
            padding=(0, 1),
        )
    )


def show_assistant_message(text: str) -> None:
    """Панель с ответом ассистента (поддерживает Markdown)."""
    console.print(
        Panel(
            Markdown(text),
            title="[assistant] Ассистент [/assistant]",
            border_style="green",
            padding=(0, 1),
        )
    )


def show_history(messages: list) -> None:
    """Выводит всю историю диалога при выходе."""
    if not messages:
        console.print(Rule("История пуста", style="dim"))
        return

    console.print()
    console.print(Rule(f"История разговора ({len(messages)} сообщений)", style="bold yellow"))

    for i, msg in enumerate(messages, 1):
        role = msg["role"]
        content = msg["content"]

        # Извлекаем текст из разных форматов контента
        if isinstance(content, str):
            text = content
        else:
            text = "\n".join(
                b.get("text", "") for b in content if b.get("type") == "text"
            )

        if role == "user":
            console.print(
                Panel(
                    text,
                    title=f"[user] Вы — сообщение {i} [/user]",
                    border_style="cyan",
                    padding=(0, 1),
                )
            )
        elif role == "assistant":
            console.print(
                Panel(
                    Markdown(text),
                    title=f"[assistant] Ассистент — сообщение {i} [/assistant]",
                    border_style="green",
                    padding=(0, 1),
                )
            )

    console.print(Rule(style="bold yellow"))


def show_token_usage(request_tokens: int, session_total: int) -> None:
    """Информационная строка с расходом токенов после ответа."""
    console.print(
        f"[info]Использовано токенов: {request_tokens:,}  ·  Всего за диалог: {session_total:,}[/info]"
    )


def show_error(message: str) -> None:
    """Сообщение об ошибке."""
    console.print(f"[error]✗ Ошибка: {message}[/error]")


def show_info(message: str) -> None:
    """Информационное сообщение."""
    console.print(f"[info]ℹ {message}[/info]")


def create_spinner(text: str = "Думаю...") -> Live:
    """Live-контекст со спиннером для ожидания ответа API."""
    return Live(
        Spinner("dots2", text=Text(f" {text}", style="dim")),
        refresh_per_second=12,
        transient=True,
    )
