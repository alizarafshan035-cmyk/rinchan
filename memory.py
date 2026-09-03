"""Per-user conversation memory: durable history + semantic recall.

Server-free stack:
- SQLite          — stores every message (chat_id, role, content, ts)
- sqlite-vec      — vector index for KNN recall, filtered per chat_id
- model2vec       — tiny pure-numpy static embeddings (no torch/onnx)

Everything lives in one file (groqbot.db by default). All public functions are
async wrappers that run the blocking SQLite/embedding work in a thread.
"""

import asyncio
import os
import threading
import time

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

import sqlite3

import sqlite_vec
from model2vec import StaticModel

DB_PATH = os.environ.get("MEMORY_DB", "groqbot.db")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "minishlab/potion-base-8M")
EMBED_DIM = 256  # potion-base-8M output dimension

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_model: StaticModel | None = None


def _get_model() -> StaticModel:
    global _model
    if _model is None:
        _model = StaticModel.from_pretrained(EMBED_MODEL)
    return _model


def _embed(text: str) -> bytes:
    vec = _get_model().encode([text])[0]
    return sqlite_vec.serialize_float32([float(x) for x in vec])


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id      INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            role    TEXT    NOT NULL,
            content TEXT    NOT NULL,
            ts      REAL    NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, id)")
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_messages USING vec0(
            msg_id    INTEGER PRIMARY KEY,
            chat_id   INTEGER,
            embedding FLOAT[{EMBED_DIM}] distance_metric=cosine
        )
        """
    )
    conn.commit()
    _conn = conn
    return conn


def _add(chat_id: int, role: str, content: str) -> None:
    with _lock:
        conn = _connect()
        cur = conn.execute(
            "INSERT INTO messages (chat_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, time.time()),
        )
        conn.execute(
            "INSERT INTO vec_messages (msg_id, chat_id, embedding) VALUES (?, ?, ?)",
            (cur.lastrowid, chat_id, _embed(content)),
        )
        conn.commit()


def _recent(chat_id: int, limit: int) -> list[dict]:
    with _lock:
        conn = _connect()
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
    return [{"role": r, "content": c} for r, c in reversed(rows)]


def _recall(chat_id: int, query: str, k: int, exclude_recent: int) -> list[str]:
    with _lock:
        conn = _connect()
        # Ignore the most recent messages (already in the short-term window).
        recent_ids = {
            row[0]
            for row in conn.execute(
                "SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
                (chat_id, exclude_recent),
            ).fetchall()
        }
        hits = conn.execute(
            """
            SELECT msg_id, distance FROM vec_messages
            WHERE embedding MATCH ? AND chat_id = ? AND k = ?
            ORDER BY distance
            """,
            (_embed(query), chat_id, k + exclude_recent),
        ).fetchall()
        out = []
        for msg_id, _dist in hits:
            if msg_id in recent_ids:
                continue
            row = conn.execute(
                "SELECT role, content FROM messages WHERE id = ?", (msg_id,)
            ).fetchone()
            if row:
                out.append(f"{row[0]}: {row[1]}")
            if len(out) >= k:
                break
    return out


def _clear(chat_id: int) -> None:
    with _lock:
        conn = _connect()
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM vec_messages WHERE chat_id = ?", (chat_id,))
        conn.commit()


# Async wrappers -------------------------------------------------------------

async def add(chat_id: int, role: str, content: str) -> None:
    await asyncio.to_thread(_add, chat_id, role, content)


async def recent(chat_id: int, limit: int) -> list[dict]:
    return await asyncio.to_thread(_recent, chat_id, limit)


async def recall(chat_id: int, query: str, k: int = 4, exclude_recent: int = 0) -> list[str]:
    return await asyncio.to_thread(_recall, chat_id, query, k, exclude_recent)


async def clear(chat_id: int) -> None:
    await asyncio.to_thread(_clear, chat_id)


def warmup() -> None:
    """Open the DB and load the embedding model up front (called at startup)."""
    _connect()
    _get_model()
