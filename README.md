# 🤖 groqbot

> A Telegram bot that texts back like a real person — streaming replies from **Groq**, with web search, voice transcription, and a memory that actually remembers.

Powered by `openai/gpt-oss-20b` on Groq's blazing-fast inference. It streams tokens live, recalls past conversations semantically, searches the web when it needs fresh facts, and listens to your voice notes. No human-in-the-loop, no corporate chatbot energy. 💬

---

## ✨ Features

- ⚡ **Live token streaming** — replies appear word-by-word by editing the message in place, throttled to stay under Telegram's rate limits.
- 🧠 **Long + short-term memory** — recent messages are replayed verbatim; older relevant ones are surfaced via semantic search (SQLite + `sqlite-vec` + tiny pure-numpy embeddings, no server, no torch).
- 🔎 **Web search** — calls DuckDuckGo on the fly for current events, prices, and anything past its training cutoff, with recency filters.
- 🎙️ **Voice notes** — transcribes voice/audio messages with Groq Whisper, then replies.
- 📝 **Markdown rendering** — final replies render as Telegram **MarkdownV2**, with long answers split across messages (4096-char limit).
- 🗣️ **Human-sounding** — a tuned system prompt keeps replies short, casual, and un-robotic. No em dashes, no "Certainly!", no emoji spam.

## 🚀 Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Copy the example env and fill in your own keys:

```bash
cp .env.example .env
```

| Variable | What it is |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `GROQ_API_KEY` | API key from [console.groq.com/keys](https://console.groq.com/keys) |
| `GROQ_MODEL` | Chat model (default `openai/gpt-oss-20b`) |
| `WHISPER_MODEL` | Transcription model (default `whisper-large-v3-turbo`) |
| `OWNER_CHAT_ID` | *(optional)* Forward all incoming messages to this chat ID |

## ▶️ Run

```bash
.venv/bin/python bot.py
```

Then open Telegram and message your bot. 🎉

## 💬 Slash Commands

| Command | Does |
| --- | --- |
| `/start` | Intro message |
| `/reset` | Wipe this chat's memory and start fresh 🧹 |
| `/id` | Reply with your numeric chat ID |
| *any text* | Get a streamed Markdown answer |
| *voice note* | Get it transcribed, then answered 🎙️ |

## 🧩 How it works

```
Telegram ──► bot.py ──► Groq (chat + Whisper)
                │
                ├─► web_search (DuckDuckGo) when fresh facts are needed
                │
                └─► memory.py ──► SQLite + sqlite-vec (per-chat history & recall)
```

## 📂 Project layout

| File | Purpose |
| --- | --- |
| `bot.py` | Telegram handlers, streaming renderer, tool-calling loop |
| `memory.py` | Per-chat durable history + semantic recall |
| `requirements.txt` | Pinned dependencies |
| `.env.example` | Template for your secrets |

## 📜 License

MIT — see [LICENSE](LICENSE).
