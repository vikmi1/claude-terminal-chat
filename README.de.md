[English](README.md) · **Deutsch** · [Русский](README.ru.md)

# AI Console — Terminal-Chat mit Claude

Ein Chat-Assistent für das Terminal auf Basis von Anthropic Claude, mit Denkmodus (Thinking), Streaming-Ausgabe und einem Gesprächsverlauf, der zwischen Sitzungen erhalten bleibt.

## So sieht es aus

![Sitzung im Terminal: Auswahl von Modus und Modell, Frage und Antwort mit Markdown-Formatierung](screenshots/chat.png)

Die Oberfläche der Anwendung ist auf Russisch.

---

## Funktionen

- **Drei Modi** — Thinking, Standard, Live-Übertragung
- **Modellauswahl** — die Liste der aktuellen Modelle wird bei jedem Start über die API geladen
- **Kontextgedächtnis** — der gesamte Verlauf wird mit jeder Anfrage gesendet, das Modell kennt das ganze Gespräch
- **Dauerhafter Verlauf** — das Gespräch wird in `chat_history.json` gespeichert und beim nächsten Start geladen
- **Ansprechende Ausgabe** — Rich-Panels mit Farbkennzeichnung und Markdown-Darstellung der Antworten
- **Steuerbefehle** — `mode`, `clear`, `help`, `exit`

---

## Modi

| # | Modus | Beschreibung |
|---|-------|----------|
| 1 | **Thinking** | Das Modell denkt vor der Antwort nach. Der Denkblock wird **nach** Abschluss der Generierung angezeigt |
| 2 | **Standard** | Antwort ohne internes Nachdenken. Schneller und günstiger |
| 3 | **Live-Übertragung** | Das Nachdenken des Modells wird **in Echtzeit** während der Generierung angezeigt |

---

## Befehle im Chat

| Befehl       | Aktion |
|--------------|----------|
| `exit`       | Verlauf speichern und Programm beenden |
| `clear`      | Gesprächsverlauf löschen (entfernt `chat_history.json`) |
| `mode`       | Menü zum Wechseln von Modus und Modell ohne Neustart öffnen |
| `help`       | Liste der verfügbaren Befehle anzeigen |
| `summarize`  | Verlauf durch Zusammenfassung verdichten |

---

## Installation und Start

### 1. Voraussetzungen

- Python 3.10+
- Ein API-Schlüssel aus der [Anthropic Console](https://console.anthropic.com/)

### 2. Projekt klonen

```bash
git clone https://github.com/vikmi1/claude-terminal-chat.git
cd claude-terminal-chat
```

### 3. Virtuelle Umgebung anlegen (empfohlen)

```bash
python -m venv .venv
```

Aktivieren:
- Windows: `.venv\Scripts\activate`
- macOS/Linux: `source .venv/bin/activate`

### 4. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 5. API-Schlüssel hinzufügen

Im Projektordner eine Datei `.env` anlegen:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 6. Starten

```bash
python main.py
```

---

## Projektstruktur

```
├── main.py           # Einstiegspunkt, Menüs, Hauptschleife des Dialogs
├── chat.py           # API-Client, generate_response und stream_response
├── display.py        # Darstellung mit Rich
├── history.py        # Speichern und Laden des Verlaufs (JSON)
├── requirements.txt  # Python-Abhängigkeiten
├── .env              # API-Schlüssel (nicht in git einchecken)
└── chat_history.json # Wird bei der ersten Nachricht automatisch angelegt
```

---

## Abhängigkeiten

| Paket | Zweck |
|-------|-----------|
| `anthropic` | Offizielles Python-SDK für die Claude API |
| `python-dotenv` | Lädt Umgebungsvariablen aus `.env` |
| `rich` | Ansprechende Terminal-Ausgabe: Panels, Markdown, Spinner |

---

## Modelle

Beim Start wird die Liste der Modelle über die API geladen — angezeigt werden alle Modelle, die für Ihr Konto verfügbar sind. Modelle mit der Markierung **thinking** unterstützen die Modi 1 und 3.

Anthropic-Modelle zum Zeitpunkt der Erstellung:

| Modell | ID | Thinking |
|--------|----|:--------:|
| Claude Opus 4.8 | `claude-opus-4-8` | ✓ |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | ✓ |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | — |

---

## Hinweise

- `MAX_TOKENS = 2000` für den Standardmodus, `MAX_TOKENS_THINKING = 16000` für die Denkmodi — einstellbar in `chat.py`
- Der Verlauf wird als JSON mit allen Inhaltsblöcken gespeichert, einschließlich der Thinking-Blöcke, die an die API zurückgesendet werden, damit mehrstufige Dialoge korrekt funktionieren
- Beim Modellwechsel mit `mode` bleibt der aktuelle Verlauf erhalten und das Gespräch wird mit dem neuen Modell fortgesetzt
