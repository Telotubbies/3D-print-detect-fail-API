import cv2
from ultralytics import YOLO

# โหลดโมเดล
model = YOLO("best.pt")

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # ✅ ใช้กล้อง index 0 และ backend DSHOW บน Windows
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

CONFIDENCE_THRESHOLD = 0.1  # ความมั่นใจขั้นต่ำ

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ ไม่สามารถอ่านภาพจากกล้องได้")
        break

    results = model(frame)[0]

    for box in results.boxes:
        conf = float(box.conf)
        if conf < CONFIDENCE_THRESHOLD:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_id = int(box.cls[0])
        label = model.names[cls_id]
        text = f"{label} {conf:.2f}"

        # ✅ สีเขียวสด
        color = (0, 255, 0)

        # ✅ วาดกรอบเขียวหนา ๆ
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

        # ✅ ทำ background สีเขียวอ่อนใต้ข้อความ
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - th - baseline), (x1 + tw, y1), color, -1)

        # ✅ วาดข้อความเป็นสีดำบนพื้นเขียว
        cv2.putText(frame, text, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    cv2.imshow("Custom YOLOv8 Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
