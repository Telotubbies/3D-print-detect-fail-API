# backend/cards.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Header, Request, Response
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import os
import secrets
import asyncio
import httpx

from backend.model import detect  # ต้องรองรับ detect(..., out_dir=Path)
from backend.schemas import Card
from backend.config import ALLOWED_MIME, MAX_FILE_SIZE, KEY_TTL, MODEL_PATH
from . import database as db

# temp store (ไฟล์ชั่วคราว + ตั้งเวลาลบ)
from backend.temp_store import (
    save_upload,            # save_upload(session_id, filename, data) -> Path
    schedule_cleanup,       # schedule_cleanup(Path, delay=TTL_SECONDS)
    session_dir,            # session_dir(session_id) -> Path
    TTL_SECONDS,
)

router = APIRouter()
SESSION_COOKIE = "session_id"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 วัน


# ---------- helpers ----------
def _validate_upload(image: UploadFile) -> None:
    if image.content_type not in ALLOWED_MIME:
        raise HTTPException(400, "Only JPEG/PNG allowed")


def _get_or_set_session_id(request: Request, response: Response) -> str:
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        return sid
    sid = secrets.token_urlsafe(16)
    # อายุ cookie ยาวกว่าไฟล์ temp (เพื่อคง session เดิมไว้)
    response.set_cookie(
        SESSION_COOKIE,
        sid,
        max_age=SESSION_MAX_AGE,     # อายุ cookie 30 วัน
        httponly=True,
        samesite="lax"
    )
    return sid


def _make_card_payload(card_id: str, sid: str, result_name: str, res: Dict) -> Dict:
    """สร้าง payload มาตรฐานคืนให้ frontend"""
    return {
        "card_id": card_id,
        "detected_image_url": f"/temp/results/{sid}/{result_name}",
        "status": res.get("status", "processed"),
        "scores": res.get("scores", {}),
        "updated_at": res.get("updated_at"),
        "model": os.path.basename(MODEL_PATH),
    }


# webhook fire-and-forget
async def notify_callback(callback_url: str, payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(callback_url, json=payload)
    except Exception as e:
        print(f"[callback] POST {callback_url} failed: {e}")


# ---------- endpoints ----------
@router.post("/cards", response_model=Card, status_code=201)
async def create_card(
    request: Request,
    response: Response,
    image: UploadFile = File(...),
):
    # 1) validate + อ่านไฟล์
    _validate_upload(image)
    content = await image.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 20MB)")

    # 2) session + card id
    sid = _get_or_set_session_id(request, response)
    card_id = secrets.token_hex(4)  # 8 ตัว เช่น uuid4().hex[:8] ก็ได้

    # 3) เซฟไฟล์อัปโหลดลง temp (ตั้งเวลาลบ)
    up_path: Path = save_upload(sid, image.filename, content)
    asyncio.create_task(schedule_cleanup(up_path, delay=TTL_SECONDS))

    # 4) รันโมเดล → เซฟผลไว้ใน temp ของ session เดียวกัน
    out_dir = session_dir(sid)  # เช่น /tmp/3dprint_tmp/<sid>/
    res = detect(content, card_id=card_id, out_dir=out_dir)

    result_name = res.get("result_name")
    if not result_name:
        # fallback: เผื่อ detect คืน path มาแทน
        result_path = Path(res.get("detected_image_path", ""))
        if result_path.exists():
            result_name = result_path.name
        else:
            raise HTTPException(500, "Detection output missing")

    # 5) ตั้งเวลาลบไฟล์ผลลัพธ์
    result_path = out_dir / result_name
    asyncio.create_task(schedule_cleanup(result_path, delay=TTL_SECONDS))

    # 6) upsert DB + คืน payload
    payload = _make_card_payload(card_id, sid, result_name, res)
    db.upsert_card(payload)
    return payload


@router.post("/cards/{card_id}/apikey")
async def get_apikey(card_id: str):
    # สร้าง API key ใหม่ให้ card เดิม (TTL = KEY_TTL)
    # หมายเหตุ: ไม่บังคับให้มี card ใน DB ก่อนก็ได้ แต่แนะนำให้มี
    rec = db.create_apikey(card_id, KEY_TTL)
    return rec


@router.post("/cards/{card_id}/replace", response_model=Card)
async def replace_card(
    request: Request,
    response: Response,
    card_id: str,
    image: UploadFile = File(...),
    x_api_key: Optional[str] = Header(default=None),
    x_callback_url: Optional[str] = Header(default=None),
):
    # 1) api key
    if not x_api_key:
        raise HTTPException(401, "Missing API key")
    if not db.verify_apikey(x_api_key, card_id):
        raise HTTPException(401, "API key expired/invalid")

    # 2) validate + session
    _validate_upload(image)
    content = await image.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 20MB)")

    sid = _get_or_set_session_id(request, response)

    # 3) เซฟอัปโหลด (optional) + cleanup
    up_path: Path = save_upload(sid, image.filename, content)
    asyncio.create_task(schedule_cleanup(up_path, delay=TTL_SECONDS))

    # 4) detect ใหม่แล้วเซฟผลลง temp
    out_dir = session_dir(sid)
    res = detect(content, card_id=card_id, out_dir=out_dir)

    result_name = res.get("result_name")
    if not result_name:
        result_path = Path(res.get("detected_image_path", ""))
        if result_path.exists():
            result_name = result_path.name
        else:
            raise HTTPException(500, "Detection output missing")

    result_path = out_dir / result_name
    asyncio.create_task(schedule_cleanup(result_path, delay=TTL_SECONDS))

    # 5) อัปเดต DB + คืน payload (ไม่ใส่ ?v= ฝั่ง backend)
    payload = _make_card_payload(card_id, sid, result_name, res)
    payload["updated_at"] = datetime.utcnow().isoformat()
    db.upsert_card(payload)

    # 6) ถ้ามี callback URL → ส่งแบบ fire-and-forget
    if x_callback_url:
        asyncio.create_task(notify_callback(x_callback_url, payload))

    # ถ้าต้องการ one-time key: uncomment
    # db.mark_apikey_used(x_api_key)

    return payload


@router.get("/cards")
async def list_cards(limit: int = 50, cursor: str | None = None):
    items = db.list_cards(limit=limit, cursor=cursor)
    return {"items": items, "next_cursor": None}


@router.get("/cards/{card_id}", response_model=Card)
async def get_card(card_id: str):
    card = db.get_card(card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.post("/cards/genkey")
async def gen_card_and_key():
    """Gen card_id + api_key พร้อมใช้งาน (ทางลัดแบบรวดเดียว)"""
    card_id = secrets.token_hex(4)

    # บันทึก card ว่าง (ให้ผ่าน NOT NULL ในตาราง)
    db.upsert_card({
        "card_id": card_id,
        "detected_image_url": "",
        "status": "PENDING",
        "scores": {},
        "updated_at": datetime.utcnow().isoformat(),
        "model": os.path.basename(MODEL_PATH),
    })
    rec = db.create_apikey(card_id, KEY_TTL)
    return {"card_id": card_id, **rec}


@router.post("/cards/gen_card")
async def gen_empty_card():
    """
    สร้าง card_id เปล่า (ยังไม่ gen key) — ใช้กรณีต้องการจอง card ไว้ก่อนค่อย upload
    """
    card_id = secrets.token_hex(4)
    db.upsert_card({
        "card_id": card_id,
        "detected_image_url": "",
        "status": "PENDING",
        "scores": {},
        "updated_at": datetime.utcnow().isoformat(),
        "model": os.path.basename(MODEL_PATH),
    })
    return {"card_id": card_id, "message": "Card created and ready for upload"}


@router.post("/cards/gen_cardkey")
async def gen_card_and_key_together():
    """
    สร้างทั้ง card_id + api_key (เทียบเท่า gen_card + genkey รวมกัน)
    """
    card_id = secrets.token_hex(4)
    db.upsert_card({
        "card_id": card_id,
        "detected_image_url": "",
        "status": "PENDING",
        "scores": {},
        "updated_at": datetime.utcnow().isoformat(),
        "model": os.path.basename(MODEL_PATH),
    })
    rec = db.create_apikey(card_id, KEY_TTL)
    return {"card_id": card_id, **rec}
@router.post("/cards/replace", response_model=Card)
async def replace_card_noid(
    request: Request,
    response: Response,
    image: UploadFile = File(...),
    x_api_key: str = Header(None),
    x_callback_url: str | None = Header(default=None),
):
    # 1) ดึง card_id จาก api_key
    if not x_api_key:
        raise HTTPException(401, "Missing API key")
    card_id = db.get_card_id_by_apikey(x_api_key)
    if not card_id:
        raise HTTPException(401, "API key expired/invalid")

    # 2) validate + session
    _validate_upload(image)
    content = await image.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 20MB)")

    sid = _get_or_set_session_id(request, response)

    # 3) เซฟอัปโหลดชั่วคราว + ตั้งเวลาลบ
    up_path: Path = save_upload(sid, image.filename, content)
    asyncio.create_task(schedule_cleanup(up_path, delay=TTL_SECONDS))

    # 4) detect แล้วเซฟผลลง temp
    out_dir = session_dir(sid)
    res = detect(content, card_id=card_id, out_dir=out_dir)

    result_name = res.get("result_name")
    if not result_name:
        result_path = Path(res.get("detected_image_path", ""))
        if result_path.exists():
            result_name = result_path.name
        else:
            raise HTTPException(500, "Detection output missing")

    result_path = out_dir / result_name
    asyncio.create_task(schedule_cleanup(result_path, delay=TTL_SECONDS))

    payload = _make_card_payload(card_id, sid, result_name, res)
    # refresh timestamp + กัน cache
    payload["updated_at"] = datetime.utcnow().isoformat()
    payload["detected_image_url"] = f"{payload['detected_image_url']}?v={secrets.token_hex(3)}"

    db.upsert_card(payload)

    if x_callback_url:
        asyncio.create_task(notify_callback(x_callback_url, payload))

    return payload