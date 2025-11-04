import cv2
import os
from ultralytics import YOLO

# โหลดโมเดลที่ฝึกเอง
model = YOLO("best.pt")

# โฟลเดอร์ input และ output
input_dir = "image"
output_dir = "output_results"
os.makedirs(output_dir, exist_ok=True)

# confidence threshold
CONF_THRESHOLD = 0.5

# loop อ่านไฟล์ภาพทั้งหมดในโฟลเดอร์
for fname in os.listdir(input_dir):
    fpath = os.path.join(input_dir, fname)

    # ข้ามถ้าไม่ใช่ไฟล์รูป
    if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
        continue

    img = cv2.imread(fpath)
    if img is None:
        print(f"❌ อ่านรูป {fname} ไม่ได้")
        continue

    # รันโมเดล
    results = model(img)[0]

    # วาดผลลัพธ์
    for box in results.boxes:
        conf = float(box.conf)
        if conf < CONF_THRESHOLD:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_id = int(box.cls[0])
        label = model.names[cls_id]
        color = (0, 255, 0)  # สีเขียว

        # วาดกรอบ
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # ใส่ label + confidence
        text = f"{label} {conf:.2f}"
        cv2.putText(img, text, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # บันทึกผลลัพธ์
    out_path = os.path.join(output_dir, fname)
    cv2.imwrite(out_path, img)
    print(f"✅ ประมวลผลแล้ว: {out_path}")

print("🎯 เสร็จสิ้น — ดูผลลัพธ์ได้ในโฟลเดอร์ output_results")
