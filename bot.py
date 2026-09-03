"""Telegram bot that streams responses from Groq (openai/gpt-oss-20b) as Markdown."""

import contextlib
import io
import warnings

# telegramify-markdown emits several DeprecationWarnings at import time *and* calls
# warnings.simplefilter("default") internally, which clobbers any filter set
# beforehand. So import it with stderr muted to swallow the import-time spam, then
# re-assert an ignore filter — this both undoes its global filter pollution and
# silences python-telegram-bot's runtime asyncio.iscoroutinefunction warning.
with contextlib.redirect_stderr(io.StringIO()):
    import telegramify_markdown  # noqa: F401
warnings.filterwarnings("ignore", category=DeprecationWarning)

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime

from ddgs import DDGS
from dotenv import load_dotenv

import memory
from openai import AsyncOpenAI
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest, RetryAfter
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "whisper-large-v3-turbo")
# Numeric Telegram chat ID of the owner; incoming messages are forwarded here.
OWNER_CHAT_ID = int(os.environ["OWNER_CHAT_ID"]) if os.environ.get("OWNER_CHAT_ID") else None

SYSTEM_PROMPT = (
    "You're a real person texting a friend, not an AI assistant. Talk exactly like "
    "people actually text.\n\n"
    "Rules:\n"
    "- Two sentences MAX, ever. Usually just one. Short beats complete.\n"
    "- Casual and natural. Contractions always (I'm, don't, yeah, gonna, kinda). "
    "Lowercase is fine. Start with 'and' or 'but' if it feels right.\n"
    "- Have opinions and a mood. React like a human would: 'oh nice', 'ugh', 'lol', "
    "'honestly no idea', 'wait what'. It's fine to be unsure, blunt, or have a take.\n"
    "- Don't over-explain or hedge. Don't list things out. Don't lecture. If someone "
    "asks something big, give the gist in a line, don't write an essay.\n"
    "- Never sound like a chatbot. No 'Certainly!', no 'I'd be happy to help', no "
    "'Great question', no corporate politeness, no emoji spam, no markdown headers "
    "or bullet points. No em dashes.\n"
    "- Don't end every message with a follow-up question. Sometimes just answer and stop.\n\n"
    "Basically: if a reply sounds like it came from an AI, rewrite it the way a normal "
    "person would actually say it out loud."
)
RECENT_MSGS = 20             # short-term window: recent messages replayed verbatim
RECALL_K = 4                 # long-term: semantically relevant older messages to surface
TELEGRAM_LIMIT = 4096        # max characters per Telegram message
EDIT_INTERVAL = 0.8          # seconds between streaming edits (rate-limit friendly)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("primp").setLevel(logging.WARNING)
log = logging.getLogger("groqbot")

groq = AsyncOpenAI(
    api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1"
)


def clean(text: str) -> str:
    """Strip em dashes (an AI tell), collapsing surrounding spaces into one."""
    return re.sub(r" *— *", " ", text)


def render(text: str) -> str:
    """Convert standard Markdown into Telegram-safe MarkdownV2."""
    return telegramify_markdown.markdownify(text)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web via DuckDuckGo for current, factual, or niche info. "
                "Use it for recent events, prices, news, or anything you're not sure "
                "about or that may have changed after your training."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The search query. For time-sensitive topics, include the "
                            "current year/month so results are fresh."
                        ),
                    },
                    "recency": {
                        "type": "string",
                        "enum": ["day", "week", "month", "year"],
                        "description": (
                            "Restrict results to the last day/week/month/year. Use a "
                            "tight window (day/week) for news and fast-changing topics."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    }
]


RECENCY = {"day": "d", "week": "w", "month": "m", "year": "y"}


async def web_search(query: str, recency: str | None = None, max_results: int = 6) -> str:
    """Run a DuckDuckGo text search and return results as a compact text block.

    `recency` (day/week/month/year) maps to DuckDuckGo's timelimit so the model
    can bias toward fresh results for news and fast-changing topics.
    """
    query = (query or "").strip()
    if not query:
        return "No query provided."
    timelimit = RECENCY.get(recency)

    def _search():
        with DDGS() as ddg:
            # When recency is requested, try the news endpoint first: results carry
            # real publish dates and come sorted newest-first. It can come back empty
            # (or raise) for non-news queries, so always fall back to plain text
            # search, which is the reliable relevance baseline.
            if timelimit:
                try:
                    news = list(
                        ddg.news(query, region="us-en", timelimit=timelimit, max_results=max_results)
                    )
                    news.sort(key=lambda r: r.get("date", ""), reverse=True)
                    if news:
                        return [
                            {
                                "title": r.get("title", ""),
                                "body": r.get("body", ""),
                                "url": r.get("url", ""),
                                "date": (r.get("date", "") or "")[:10],
                                "source": r.get("source", ""),
                            }
                            for r in news
                        ]
                except Exception as e:  # noqa: BLE001
                    log.info("news search empty/failed, falling back to text: %s", e)
            return [
                {"title": r.get("title", ""), "body": r.get("body", ""), "url": r.get("href", "")}
                for r in ddg.text(query, region="us-en", max_results=max_results)
            ]

    try:
        results = await asyncio.to_thread(_search)
    except Exception as e:  # noqa: BLE001
        log.warning("web_search failed: %s", e)
        return f"Search failed: {e}"
    if not results:
        return "No recent results found." if timelimit else "No results found."

    header = f"Web results for '{query}'"
    if recency:
        header += f" (last {recency}, newest first)"
    header += f" — today is {datetime.now():%Y-%m-%d}:"
    blocks = []
    for i, r in enumerate(results, 1):
        meta = ""
        if r.get("date"):
            meta = f" ({r['date']}, {r.get('source', '')})"
        blocks.append(f"[{i}]{meta} {r['title']}\n{r['body']}\n{r['url']}")
    return header + "\n\n" + "\n\n".join(blocks)


async def run_tool(name: str, raw_args: str) -> str:
    """Dispatch a tool call by name; returns a string result for the model."""
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        args = {}
    if name == "web_search":
        return await web_search(args.get("query", ""), args.get("recency"))
    return f"Unknown tool: {name}"


class StreamRenderer:
    """Manages a (possibly multi-message) streaming reply, editing in place.

    Streams as plain text while generating (cheap, never breaks on partial
    markdown), then re-renders each message as MarkdownV2 when finalized.
    """

    def __init__(self, bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.messages: list = []   # sent telegram Message objects
        self.parts: list[str] = []  # text content per message
        self._last_edit = 0.0

    async def _send_new(self, text: str):
        msg = await self.bot.send_message(chat_id=self.chat_id, text=text or "…")
        self.messages.append(msg)
        self.parts.append(text)

    async def _edit(self, idx: int, text: str, markdown: bool = False):
        kwargs = {}
        if markdown:
            text = render(text)
            kwargs["parse_mode"] = ParseMode.MARKDOWN_V2
        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.messages[idx].message_id,
                text=text or "…",
                **kwargs,
            )
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 0.5)
            await self._edit(idx, text, markdown)
        except BadRequest as e:
            if "not modified" in str(e).lower():
                return
            raise

    async def update(self, full_text: str, force: bool = False):
        """Feed the latest accumulated text; throttles edits unless forced."""
        now = time.monotonic()
        if not force and now - self._last_edit < EDIT_INTERVAL:
            return
        self._last_edit = now

        # Split the full text into Telegram-sized parts.
        chunks = _split(full_text, TELEGRAM_LIMIT)
        if not chunks:
            chunks = [""]

        for i, chunk in enumerate(chunks):
            if i >= len(self.messages):
                await self._send_new(chunk)
            elif self.parts[i] != chunk:
                self.parts[i] = chunk
                await self._edit(i, chunk)

    async def finalize(self, full_text: str):
        """Re-render every message as Markdown once streaming is complete."""
        chunks = _split(full_text, TELEGRAM_LIMIT) or [""]
        for i, chunk in enumerate(chunks):
            if i >= len(self.messages):
                # Markdown expands length; send as plain then render.
                await self._send_new(chunk)
            try:
                await self._edit(i, chunk, markdown=True)
            except BadRequest:
                # Fall back to plain text if rendering produced invalid entities.
                await self._edit(i, chunk, markdown=False)


def _split(text: str, limit: int) -> list[str]:
    """Split text into <=limit chunks, preferring newline boundaries."""
    if len(text) <= limit:
        return [text] if text else []
    parts, remaining = [], text
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = window.rfind("\n")
        if cut < limit // 2:  # no good newline; hard-cut
            cut = limit
        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        parts.append(remaining)
    return parts


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("hey! what's on your mind?")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await memory.clear(update.effective_chat.id)
    await update.message.reply_text("🧹 wiped, fresh start.")


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your chat ID is `{update.effective_chat.id}`")


async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward every incoming message to the owner (skips the owner's own messages)."""
    if OWNER_CHAT_ID is None or update.effective_chat.id == OWNER_CHAT_ID:
        return
    try:
        await context.bot.forward_message(
            chat_id=OWNER_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )
    except Exception:  # noqa: BLE001
        log.exception("Failed to forward message to owner")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_reply(update.effective_chat.id, update.message.text, context)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe a voice/audio message with Groq Whisper, then reply with text."""
    chat_id = update.effective_chat.id
    media = update.message.voice or update.message.audio
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    try:
        tg_file = await context.bot.get_file(media.file_id)
        audio = bytes(await tg_file.download_as_bytearray())
        result = await groq.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=("voice.ogg", audio),
        )
        user_text = (result.text or "").strip()
    except Exception as e:  # noqa: BLE001
        log.exception("Transcription failed")
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Couldn't transcribe that: {e}")
        return

    if not user_text:
        await context.bot.send_message(chat_id=chat_id, text="hmm, couldn't make out anything in that")
        return
    await generate_reply(chat_id, user_text, context)


async def generate_reply(chat_id: int, user_text: str, context: ContextTypes.DEFAULT_TYPE):
    # Short-term: replay the recent window. Long-term: semantically recall older
    # messages relevant to what was just said (scoped to this user).
    recent = await memory.recent(chat_id, RECENT_MSGS)
    recalled = await memory.recall(chat_id, user_text, k=RECALL_K, exclude_recent=RECENT_MSGS)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Today's date is {datetime.now():%A, %B %d, %Y}."},
    ]
    if recalled:
        messages.append({
            "role": "system",
            "content": "Relevant things from earlier conversations:\n" + "\n".join(recalled),
        })
    messages.extend(recent)
    messages.append({"role": "user", "content": user_text})

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    renderer = StreamRenderer(context.bot, chat_id)
    answer = ""

    try:
        # Stream the reply; if the model calls tools (e.g. web_search), run them,
        # feed results back, and stream again. A few rounds max to avoid loops.
        for _ in range(4):
            stream = await groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                stream=True,
                temperature=0.8,
                max_tokens=800,
                reasoning_effort="low",
                tools=TOOLS,
                tool_choice="auto",
            )
            answer = ""
            calls: dict[int, dict] = {}
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    answer += delta.content
                    await renderer.update(clean(answer))
                for tc in delta.tool_calls or []:
                    slot = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["args"] += tc.function.arguments

            if not calls:
                break  # final answer streamed

            ordered = [calls[i] for i in sorted(calls)]
            messages.append({
                "role": "assistant",
                "content": answer or None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["args"]},
                    }
                    for c in ordered
                ],
            })
            for c in ordered:
                log.info("tool call: %s(%s)", c["name"], c["args"])
                result = await run_tool(c["name"], c["args"])
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": result})
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        text = clean(answer) or "_(no response)_"
        await renderer.finalize(text)

        await memory.add(chat_id, "user", user_text)
        await memory.add(chat_id, "assistant", text)
    except Exception as e:  # noqa: BLE001
        log.exception("Generation failed")
        err = f"⚠️ Error: {e}"
        if renderer.messages:
            await renderer._edit(0, err)
        else:
            await context.bot.send_message(chat_id=chat_id, text=err)


def main():
    log.info("Loading memory (SQLite + sqlite-vec + %s)...", memory.EMBED_MODEL)
    memory.warmup()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("id", whoami))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    # Separate group so it runs for *every* message, alongside the handlers above.
    app.add_handler(MessageHandler(filters.ALL, forward_to_owner), group=1)
    log.info("Bot started with model %s (owner=%s)", GROQ_MODEL, OWNER_CHAT_ID)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
