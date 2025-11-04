#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
import requests
import cv2
import numpy as np
from io import BytesIO
import time

BASE_URL = "https://g1tuesm.consolutechcloud.com"

class GetApiNode(Node):
    def __init__(self):
        super().__init__('get_api_node')

        # Publisher
        self.publisher_ = self.create_publisher(Int32, 'api_input', 10)

        # Timer — ถ่ายภาพทุก 60 วินาที
        self.timer = self.create_timer(60.0, self.timer_callback)

        self.get_logger().info("🚀 get_api_node started (capture every 60s)")

    def timer_callback(self):
        try:
            card_id, api_key = self.get_api_key()
            image_bytes = self.capture_image()
            result = self.upload_image(card_id, api_key, image_bytes)

            status = result.get("status", "UNKNOWN")
            detected_url = result.get("detected_image_url")

            # แสดงผลใน log
            self.get_logger().info(f"🟢 Detection Status: {status}")

            # ส่งค่า api ไปยัง topic
            msg = Int32()
            msg.data = 0 if status.upper() == "NORMAL" else 1
            self.publisher_.publish(msg)
            self.get_logger().info(f"📡 Published api={msg.data} to /api_input")

            # (เลือกได้) แสดงภาพผลลัพธ์
            #if detected_url:
            #    self.show_detected_image(detected_url)

        except Exception as e:
            self.get_logger().error(f"🔥 Error: {e}")

    def get_api_key(self):
        url = f"{BASE_URL}/cards/genkey"
        resp = requests.post(url)
        if resp.status_code == 200:
            data = resp.json()
            self.get_logger().info(f"✅ Generated key: {data}")
            return data["card_id"], data["api_key"]
        else:
            raise RuntimeError(f"Failed to generate key: {resp.status_code} {resp.text}")

    def capture_image(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("❌ Cannot open webcam")

        time.sleep(2)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise RuntimeError("❌ Failed to capture image")

        _, buffer = cv2.imencode(".jpg", frame)
        image_bytes = BytesIO(buffer.tobytes())
        return image_bytes

    def upload_image(self, card_id, api_key, image_bytes):
        url = f"{BASE_URL}/cards/{card_id}/replace"
        headers = {"x-api-key": api_key}
        files = {"image": ("frame.jpg", image_bytes, "image/jpeg")}
        resp = requests.post(url, headers=headers, files=files)
        if resp.status_code == 200:
            data = resp.json()
            self.get_logger().info("✅ Upload successful!")
            return data
        else:
            raise RuntimeError(f"❌ Upload failed: {resp.status_code} {resp.text}")

    def show_detected_image(self, relative_url):
        full_url = f"{BASE_URL}{relative_url}"
        resp = requests.get(full_url, stream=True)
        if resp.status_code == 200:
            img_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            cv2.imshow("AI Detection Result", img)
            cv2.waitKey(1000)  # แสดง 1 วินาที
            cv2.destroyAllWindows()
        else:
            self.get_logger().warn(f"⚠️ Failed to load result image: {resp.status_code}")


def main(args=None):
    rclpy.init(args=args)
    node = GetApiNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("🛑 Node stopped manually.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

