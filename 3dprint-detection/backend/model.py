import os, datetime
import cv2
import numpy as np
from pathlib import Path
import torch
from ultralytics import YOLO
from backend.config import MODEL_PATH, CONF_THRESHOLD, RESULT_DIR

torch.serialization.add_safe_globals([
    torch.nn.modules.container.Sequential,
    torch.nn.Module,
    YOLO.__class__,
])

MODEL_PATH = "backend/best.pt"
model = YOLO(MODEL_PATH)

def detect(image_bytes: bytes, card_id: str, out_dir: Path):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    results = model.predict(img, conf=CONF_THRESHOLD)[0]
    scores = {}

    has_non_3dprint = False
    has_detection = len(results.boxes) > 0
    print("Number of detections:", len(results.boxes))

    for i, box in enumerate(results.boxes):
        xyxy = box.xyxy[0].cpu().numpy().astype(int)
        conf = float(box.conf[0].cpu().numpy())
        cls_id = int(box.cls[0].cpu().numpy())
        label = model.names.get(cls_id, f"class_{cls_id}")

        if cls_id not in [0, 1]:
            has_non_3dprint = True

        scores[label] = max(scores.get(label, 0.0), conf)
        print(f"Box {i}: Class={label}, Conf={conf:.2f}, XYXY={xyxy}")

        # --- กำหนดสีกรอบตามคลาส ---
        if cls_id == 0:
            color = (0, 255, 0)     # Green = normal
        elif cls_id == 1:
            color = (0, 0, 255)     # Red = spaghetti
        else:
            color = (255, 0, 0)     # Blue = not 3d part

        # --- วาดกรอบ detection ---
        cv2.rectangle(img, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)

        # --- เตรียมข้อความและพื้นหลัง ---
        label_text = f"{label} {conf:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 2
        font_thickness = 2

        # คำนวณขนาดกล่องพื้นหลังให้พอดีกับข้อความ
        (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, font_thickness)
        text_x, text_y = xyxy[0], max(20, xyxy[1] - 10)  # ตำแหน่งข้อความเหนือกรอบ

        # พื้นหลังสีเดียวกับกรอบแต่โปร่งเล็กน้อย
        bg_color = tuple(int(c * 0.5) for c in color)
        cv2.rectangle(img, (text_x - 2, text_y - text_h - 2),
                      (text_x + text_w + 2, text_y + 4),
                      bg_color, -1)
        # วาดข้อความทับบนพื้นหลัง
        cv2.putText(img, label_text, (text_x, text_y),
                    font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

    # --- ตัดสินผลรวม ---
    if not has_detection:
        status = "NOT_3DPRINT_PART"
    elif has_non_3dprint:
        status = "NOT_3DPRINT_PART"
    elif scores.get("spaghetti", 0.0) >= CONF_THRESHOLD:
        status = "FAIL"
    else:
        status = "NORMAL"

    # --- บันทึกไฟล์ผลลัพธ์ ---
    out_dir.mkdir(parents=True, exist_ok=True)
    result_name = f"{card_id}_latest.jpg"
    result_path = out_dir / result_name
    cv2.imwrite(str(result_path), img)
    print("Saved temp result:", result_path)

    return {
        "result_name": result_name,
        "scores": scores,
        "status": status,
        "updated_at": datetime.datetime.utcnow().isoformat()
    }
