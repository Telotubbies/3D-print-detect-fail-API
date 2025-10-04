import os
from backend.config import UPLOAD_DIR

os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_upload(card_id: str, filename: str, content: bytes) -> str:
    ext = os.path.splitext(filename)[1]
    path = os.path.join(UPLOAD_DIR, f"{card_id}{ext}")
    with open(path, "wb") as f:
        f.write(content)
    return path
