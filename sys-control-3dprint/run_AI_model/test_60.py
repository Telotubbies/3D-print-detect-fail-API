import cv2
import time
from ultralytics import YOLO

# โหลดโมเดล YOLO
model = YOLO("best.pt")

# ชื่อคลาส (แก้ให้ตรงกับ classes ของโมเดลคุณ)
class_names = ["normal print", "printer head", "spaghettis"]

normal_print = 0
printer_head = 0
spaghettis = 0


def run_detection():
    # เปิดกล้อง (0 หรือ 1 ตามกล้องที่คุณใช้)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Unable to open camera")
        return

    # อ่านเฟรมเดียว
    ret, frame = cap.read()
    if ret:
        # รัน YOLO บนเฟรมเดียว
        results = model(frame)

        # ✅ ดึงข้อมูลการตรวจจับ
        detections = results[0].boxes
        classes = detections.cls.tolist()  # index ของคลาสที่เจอ

        # ✅ นับจำนวนแต่ละคลาส
        counts = {name: 0 for name in class_names}
        for cls_id in classes:
            cls_name = class_names[int(cls_id)]
            counts[cls_name] += 1

        # ✅ แสดงผลลัพธ์
        # print("📊 ผลการตรวจจับ:", counts)

        # แมปเป็น uint8_t (ใช้ numpy.uint8)
        normal_print = counts["normal print"]
        printer_head = counts["printer head"]
        spaghettis = counts["spaghettis"]

        print("normal_print =", normal_print)
        print("printer_head =", printer_head)
        print("spaghettis   =", spaghettis)

        # วาดผลลัพธ์
        # annotated_frame = results[0].plot()

        # # แสดงภาพ
        # cv2.imshow("YOLO Detection", annotated_frame)
        # cv2.waitKey(2000)  # แสดงผล 2 วินาที
        # cv2.destroyAllWindows()

    cap.release()


# 📌 วนรอบทุกๆ 60 วินาที
while True:
    print("photos with a camera")
    run_detection()

    print("... wait 60 s ...")
    time.sleep(60)
