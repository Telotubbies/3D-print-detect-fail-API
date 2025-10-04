# backend/temp_store.py
import secrets
import shutil
import tempfile
from pathlib import Path
from typing import Tuple
import asyncio
import time

# โฟลเดอร์ temp กลางของระบบ
TMP_ROOT = Path(tempfile.gettempdir()) / "3dprint_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)

# อายุไฟล์/โฟลเดอร์ (วินาที) — ปรับได้ตามต้องการ
TTL_SECONDS = 60 * 60 * 24  # 1 วัน (แนะนำ: 1 ชม.=3600, 7 วัน=604800)

def session_dir(session_id: str) -> Path:
    d = TMP_ROOT / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def save_upload(session_id: str, filename: str, data: bytes) -> Path:
    """
    เซฟไฟล์อัปโหลดไว้ที่โฟลเดอร์ของ session และตั้งเวลาลบระดับ "ทั้งโฟลเดอร์"
    (ทำให้ภายใน session เดียวกัน ต่ออายุง่าย)
    """
    d = session_dir(session_id)
    p = d / filename
    p.write_bytes(data)
    # ตั้งเวลาลบระดับโฟลเดอร์ (ซ้ำได้ ไม่เป็นไร) — เหมาะกับ sliding TTL
    asyncio.create_task(schedule_cleanup(d, delay=TTL_SECONDS))
    return p

def list_session_files(session_id: str):
    d = TMP_ROOT / session_id
    if not d.exists():
        return []
    return [p.name for p in d.iterdir()]

async def schedule_cleanup(path_or_session: Path, delay: int = TTL_SECONDS):
    """
    ตั้งเวลาลบไฟล์/โฟลเดอร์หลัง delay วินาที
    เรียกซ้ำได้ (ไม่ต้องยกเลิกงานเก่า) เพราะลบแบบ ignore_errors
    """
    await asyncio.sleep(delay)
    try:
        if path_or_session.is_file():
            path_or_session.unlink(missing_ok=True)
        elif path_or_session.is_dir():
            shutil.rmtree(path_or_session, ignore_errors=True)
    except Exception:
        # เงียบไว้เพื่อไม่ให้ crash background task
        pass

def bump_session_ttl(session_id: str, delay: int = TTL_SECONDS) -> None:
    """
    ต่ออายุโฟลเดอร์ของ session (sliding TTL)
    เรียกทุกครั้งที่มีการเข้าถึงไฟล์ใน session นั้น ๆ
    """
    d = session_dir(session_id)  # ensure exists
    # อาจ "touch" ไฟล์ marker เพื่อบอกมีการใช้งาน (optional)
    marker = d / ".last_access"
    try:
        marker.write_text(str(time.time()))
    except Exception:
        pass
    # ตั้งเวลาลบใหม่ (ซ้ำได้ ไม่เป็นไร)
    asyncio.create_task(schedule_cleanup(d, delay=delay))
