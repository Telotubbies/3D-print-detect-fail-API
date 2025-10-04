import os, datetime
import cv2
import numpy as np

from pathlib import Path

import torch
from ultralytics.nn.tasks import DetectionModel
torch.serialization.add_safe_globals([torch.nn.modules.container.Sequential])

from ultralytics import YOLO
from backend.config import MODEL_PATH, CONF_THRESHOLD, RESULT_DIR

torch.serialization.add_safe_globals([torch.nn.modules.container.Sequential])
torch.serialization.add_safe_globals([torch.nn.Module])
torch.serialization.add_safe_globals([YOLO.__class__])
MODEL_PATH = "backend/best.pt"
model = YOLO(MODEL_PATH)

def detect(image_bytes: bytes, card_id: str, out_dir: Path):
    # แปลง bytes เป็น OpenCV image
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # run YOLO
    results = model.predict(img, conf=CONF_THRESHOLD, classes=[0, 2])[0]

    scores = {}
    print("Number of detections:", len(results.boxes))

    for i, box in enumerate(results.boxes):
        xyxy = box.xyxy[0].cpu().numpy().astype(int)   # ดึงเป็น [x1, y1, x2, y2]
        conf = float(box.conf[0].cpu().numpy())
        cls_id = int(box.cls[0].cpu().numpy())
        label = model.names[cls_id]

        # เก็บค่าความมั่นใจสูงสุดของแต่ละ class
        scores[label] = max(scores.get(label, 0.0), conf)

        print(f"Box {i}: Class={label}, Conf={conf:.2f}, XYXY={xyxy}")

        # สีแดงสำหรับ spaghetti (2), สีเขียวสำหรับ normal (0)
        color = (0, 0, 255) if cls_id == 2 else (0, 255, 0)
        cv2.rectangle(img, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)
        cv2.putText(img, f"{label} {conf:.2f}", (xyxy[0], xyxy[1]-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # ตัดสินสถานะ
    if scores.get("spaghetti", 0.0) >= CONF_THRESHOLD:
        status = "FAIL"
    else:
        status = "NORMAL"

    # บันทึกไฟล์ผลลัพธ์
    # บันทึกไฟล์ผลลัพธ์ลง temp out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    result_name = f"{card_id}_latest.jpg"
    result_path = out_dir / result_name
    cv2.imwrite(str(result_path), img)
    print("Saved temp result:", result_path)

    return {
        "result_name": result_name,   # cards.py จะเอาไป wrap เป็น /temp/results/{result_name}
        "scores": scores,
        "status": status,
        "updated_at": datetime.datetime.utcnow().isoformat()
    }

