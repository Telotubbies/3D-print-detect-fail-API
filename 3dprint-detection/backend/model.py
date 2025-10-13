import datetime
import cv2
import numpy as np
from pathlib import Path
import torch
from ultralytics import YOLO
import logging

# === CONFIG SECTION ===
try:
    from backend.config import MODEL_PATH, CONF_THRESHOLD, RESULT_DIR
except ImportError:
    MODEL_PATH = "backend/best.pt"
    CONF_THRESHOLD = 0.35
    RESULT_DIR = Path("results")

# === LOGGER SETUP ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === TORCH SAFE GLOBALS ===
torch.serialization.add_safe_globals([
    torch.nn.modules.container.Sequential,
    torch.nn.Module,
    YOLO.__class__,
])

# === MODEL CACHE (load once only) ===
_model_cache = None
def get_model():
    global _model_cache
    if _model_cache is None:
        logger.info(f"Loading YOLO model from {MODEL_PATH} ...")
        _model_cache = YOLO(MODEL_PATH)
        logger.info("Model loaded successfully.")
    return _model_cache


# === MAIN DETECTION FUNCTION ===
def detect(image_bytes: bytes, card_id: str, out_dir: Path):
    """รัน YOLO ตรวจจับภาพและคืนค่าผลลัพธ์"""
    model = get_model()

    # --- Decode image ---
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("ไม่สามารถอ่านภาพจาก bytes ได้")

    # --- Run model prediction ---
    preds = model.predict(img, conf=CONF_THRESHOLD)
    if not preds or len(preds[0].boxes) == 0:
        logger.info("No detections found.")
        has_detection = False
        results = None
    else:
        has_detection = True
        results = preds[0]

    scores = {}
    has_non_3dprint = False

    if has_detection:
        logger.info(f"Number of detections: {len(results.boxes)}")

        for i, box in enumerate(results.boxes):
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())

            # --- Safe class name ---
            names = model.names
            if isinstance(names, dict):
                label = names.get(cls_id, f"class_{cls_id}")
            else:
                label = names[cls_id] if cls_id < len(names) else f"class_{cls_id}"

            # --- Check for non-3D parts ---
            if cls_id not in [0, 1]:
                has_non_3dprint = True

            # --- Update score ---
            scores[label] = max(scores.get(label, 0.0), conf)
            logger.info(f"Box {i}: Class={label}, Conf={conf:.2f}, XYXY={xyxy}")

            # --- Define box color by class ---
            if cls_id == 0:
                color = (0, 255, 0)     # Green = normal
            elif cls_id == 1:
                color = (0, 0, 255)     # Red = spaghetti
            else:
                color = (255, 0, 0)     # Blue = not 3d part

            # --- Draw box ---
            cv2.rectangle(img, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)

            # --- Prepare label text ---
            label_text = f"{label} {conf:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = max(0.5, img.shape[1] / 1000)  # auto scale
            font_thickness = 2

            # --- Calculate text background ---
            (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, font_thickness)
            text_x, text_y = xyxy[0], max(text_h + 5, xyxy[1] - 10)

            bg_color = tuple(int(c * 0.5) for c in color)
            cv2.rectangle(img, (text_x - 2, text_y - text_h - 2),
                          (text_x + text_w + 2, text_y + 4), bg_color, -1)
            cv2.putText(img, label_text, (text_x, text_y),
                        font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

    # --- Determine overall status ---
    if not has_detection:
        status = "NOT_3DPRINT_PART"
    elif scores.get("spaghetti", 0.0) > 0.0:
        status = "FAIL"
    elif has_non_3dprint:
        status = "NOT_3DPRINT_PART"
    else:
        status = "NORMAL"

    # --- Save result image ---
    out_dir.mkdir(parents=True, exist_ok=True)
    result_name = f"{card_id}_latest.jpg"
    result_path = out_dir / result_name
    cv2.imwrite(str(result_path), img)
    logger.info(f"Saved result image to {result_path}")

    # --- Return summary ---
    return {
        "result_name": result_name,
        "scores": scores,
        "status": status,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
