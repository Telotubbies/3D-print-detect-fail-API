import sqlite3
import json
import time
import secrets, hashlib
from pathlib import Path

DB_PATH = Path("backend/database.db")

DDL_CARDS = """
CREATE TABLE IF NOT EXISTS cards (
    card_id TEXT PRIMARY KEY,
    detected_image_url TEXT NOT NULL,
    status TEXT NOT NULL,               -- GOOD / FAIL
    scores_json TEXT NOT NULL,          -- {"normal print":0.0,"print header":0.0,"spaghetti":0.0}
    updated_at TEXT NOT NULL,           -- ISO8601
    model TEXT NOT NULL                 -- e.g. best.pt
);
"""

DDL_APIKEYS = """
CREATE TABLE IF NOT EXISTS apikeys (
    api_key TEXT PRIMARY KEY,           -- store SHA256 hash
    card_id TEXT NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    expires_at REAL NOT NULL,           -- epoch seconds
    used INTEGER NOT NULL DEFAULT 0     -- optional (0/1) if one-time key
);
"""

DDL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_keys_card ON apikeys(card_id);
CREATE INDEX IF NOT EXISTS idx_keys_exp ON apikeys(expires_at);
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(DDL_CARDS)
        cur.execute(DDL_APIKEYS)
        for stmt in DDL_INDEXES.strip().splitlines():
            if stmt.strip():
                cur.execute(stmt)
        conn.commit()

# ---------- Helpers ----------
def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

# --------- Cards CRUD ---------
def upsert_card(card: dict):
    """
    บันทึกหรืออัปเดตการ์ดในตาราง cards
    - ถ้า card_id ยังไม่มี → INSERT ใหม่
    - ถ้ามีแล้ว → UPDATE ค่า image, status, scores, updated_at, model
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cards (card_id, detected_image_url, status, scores_json, updated_at, model)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(card_id) DO UPDATE SET
                detected_image_url = excluded.detected_image_url,
                status = excluded.status,
                scores_json = excluded.scores_json,
                updated_at = excluded.updated_at,
                model = excluded.model
        """, (
            card["card_id"],
            card["detected_image_url"],
            card.get("status", "PENDING"),
            json.dumps(card.get("scores", {})),
            card.get("updated_at"),
            card.get("model", "unknown")
        ))
        conn.commit()

def get_card(card_id: str) -> dict | None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "card_id": row["card_id"],
            "detected_image_url": row["detected_image_url"],
            "status": row["status"],
            "scores": json.loads(row["scores_json"]),
            "updated_at": row["updated_at"],
            "model": row["model"],
        }

def list_cards(limit: int = 50, cursor: str | None = None) -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cards ORDER BY updated_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        items = []
        for r in rows:
            items.append({
                "card_id": r["card_id"],
                "detected_image_url": r["detected_image_url"],
                "status": r["status"],
                "scores": json.loads(r["scores_json"]),
                "updated_at": r["updated_at"],
                "model": r["model"],
            })
        return items

# --------- API Keys (hashed) ---------
def create_apikey(card_id: str, ttl_seconds: int) -> dict:
    """Generate key (plain), store only hash"""
    plain_key = secrets.token_urlsafe(32)
    key_hash = _sha256(plain_key)
    expires_at = time.time() + ttl_seconds

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO apikeys(api_key, card_id, expires_at, used) VALUES (?, ?, ?, 0)",
                    (key_hash, card_id, expires_at))
        conn.commit()
    return {"api_key": plain_key, "card_id": card_id, "expires_at": expires_at}

def verify_apikey(api_key: str, card_id: str) -> bool:
    now = time.time()
    key_hash = _sha256(api_key)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT card_id, expires_at, used FROM apikeys WHERE api_key = ?", (key_hash,))
        row = cur.fetchone()
        if not row:
            return False
        if row["card_id"] != card_id:
            return False
        if row["expires_at"] < now:
            return False
        if row["used"] == 1:  # already used
            return False
        return True

def mark_apikey_used(api_key: str):
    key_hash = _sha256(api_key)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE apikeys SET used = 1 WHERE api_key = ?", (key_hash,))
        conn.commit()
def get_card_id_by_apikey(api_key: str) -> str | None:
    now = time.time()
    key_hash = _sha256(api_key)   # ✅ ต้องแฮชก่อน
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT card_id, expires_at, used FROM apikeys WHERE api_key = ?",
            (key_hash,),
        )
        row = cur.fetchone()
        if not row:
            return None
        if row["expires_at"] < now:
            return None
        if row["used"] == 1:
            return None
        return row["card_id"]
