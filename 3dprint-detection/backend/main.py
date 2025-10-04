from fastapi.responses import FileResponse
from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
from backend.temp_store import TMP_ROOT
from backend import temp_store  

from . import cards
from backend.database import init_db
import mimetypes
from urllib.parse import unquote
# -----------------------------
# Init app & DB
# -----------------------------
app = FastAPI()
init_db()

# -----------------------------
# CORS middleware
# -----------------------------
# ในโปรดักชันให้เปลี่ยน allow_origins เป็นโดเมนจริง
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: ["https://prints.yourdomain.tld"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Include API router
# -----------------------------
app.include_router(cards.router)
# -----------------------------
# Serve temp results
# -----------------------------
@app.get("/temp/results/{sid}/{filename}")
def serve_result(sid: str, filename: str):
    # decode ชื่อไฟล์และกัน path traversal
    safe_name = Path(unquote(filename)).name
    p = (TMP_ROOT / sid / safe_name).resolve()

    if TMP_ROOT not in p.parents and p != TMP_ROOT:
        raise HTTPException(status_code=400, detail="invalid path")

    if not p.exists():
        raise HTTPException(status_code=404, detail="result not found or expired")

    mime, _ = mimetypes.guess_type(str(p))
    if not mime:
        mime = "application/octet-stream"

    print("[serve_result]", p, "=>", mime)  # log debug ดูว่าชี้ path ถูกไหม

    return FileResponse(
        str(p),
        media_type=mime,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )



# สำหรับไฟล์ frontend static (CSS/JS)
frontend_static = Path(__file__).resolve().parent.parent / "frontend" / "static"
app.mount("/static", StaticFiles(directory=frontend_static), name="static")

# -----------------------------
# Serve index.html
# -----------------------------
frontend_index = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

@app.get("/", response_class=HTMLResponse)
def read_index():
    return frontend_index.read_text(encoding="utf-8")
