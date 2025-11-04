#!/usr/bin/env python3
import requests
import cv2
import numpy as np
from io import BytesIO
import time

BASE_URL = "https://g1tuesm.consolutechcloud.com"


def get_api_key():
    """ขอ API key ใหม่จาก server"""
    url = f"{BASE_URL}/cards/genkey"
    resp = requests.post(url)
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Generated key: {data}")
        return data["card_id"], data["api_key"]
    else:
        raise RuntimeError(f"Failed to generate key: {resp.status_code} {resp.text}")


def capture_image():
    """ถ่ายภาพจากกล้องและคืนค่าเป็น bytes"""
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        raise RuntimeError("❌ Cannot open webcam")

    time.sleep(2)  # รอกล้องปรับโฟกัส
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError("❌ Failed to capture image")

    # แปลงเป็น JPEG bytes
    _, buffer = cv2.imencode(".jpg", frame)
    image_bytes = BytesIO(buffer.tobytes())
    return image_bytes


def upload_image(card_id, api_key, image_bytes):
    """อัปโหลดภาพไปยัง API"""
    url = f"{BASE_URL}/cards/{card_id}/replace"
    headers = {"x-api-key": api_key}
    files = {"image": ("frame.jpg", image_bytes, "image/jpeg")}
    resp = requests.post(url, headers=headers, files=files)
    if resp.status_code == 200:
        data = resp.json()
        print("✅ Upload successful!")
        print(data)
        return data
    else:
        raise RuntimeError(f"❌ Upload failed: {resp.status_code} {resp.text}")


def show_detected_image(relative_url):
    """แสดงภาพผลลัพธ์จาก API"""
    full_url = f"{BASE_URL}{relative_url}"
    print(f"📷 Showing result from: {full_url}")
    resp = requests.get(full_url, stream=True)
    if resp.status_code == 200:
        img_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        cv2.imshow("AI Detection Result", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print(f"⚠️ Failed to load result image: {resp.status_code}")


def main():
    try:
        # 1️⃣ ขอ API key
        card_id, api_key = get_api_key()

        # 2️⃣ ถ่ายภาพจากกล้อง
        image_bytes = capture_image()

        # 3️⃣ ส่งภาพขึ้นเว็บ
        result = upload_image(card_id, api_key, image_bytes)

        # 4️⃣ อ่านผลลัพธ์
        status = result.get("status", "UNKNOWN")
        print(f"🟢 Detection Status: {status}")

        # 5️⃣ แสดงภาพที่ตรวจจับได้
        detected_url = result.get("detected_image_url")
        if detected_url:
            show_detected_image(detected_url)

    except Exception as e:
        print(f"🔥 Error: {e}")


if __name__ == "__main__":
    main()
