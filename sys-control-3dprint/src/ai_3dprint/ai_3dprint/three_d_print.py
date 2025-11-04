#!/usr/bin/env python3
# ai_3dprint/three_d_print.py

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
import requests
import time

API_KEY = "QM7KcrPnZRsJtVCe6KVE5i2LrL6mKRc-CsGiE5jnYH4"
OCTOPRINT_URL = "http://localhost:5000"
HOST_URL = OCTOPRINT_URL
headers = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

clear_gcode = [
    "G90",                        # ใช้ absolute positioning
    "G1 Z0.3 F300",               # ลดหัวลงใกล้เตียง
    "G1 X110 Y1 F1500",           # ลากหัวไปข้างหน้าเล็กน้อยเพื่อเคลียร์โมเดล
]

cooldown_gcode = [
    "M104 S0",     # ปิด hotend heater
    "M140 S0",     # ปิด bed heater
    "M107",        # ปิดพัดลม
    "G91",         # relative positioning
    "G1 Z10 F600", # ยกหัวขึ้น 10mm จากตำแหน่งปัจจุบัน
    "G90",         # กลับไป absolute positioning
    "G1 X110 Y218 F3000", # ไปที่ตำแหน่งพัก
    "G1 Z0 F600",   # เลื่อนหัวลงถึง bed (Z=0)
]

def set_active(active: bool):
    """เปิดหรือปิด continuous print mode"""
    return requests.post(
        f"{HOST_URL}/plugin/continuousprint/set_active",
        headers={"X-Api-Key": API_KEY},
        data={"active": str(active).lower()},
    )


def cancel_job():
    """ยกเลิกงานปัจจุบัน"""
    data = {"command": "cancel"}
    return requests.post(f"{OCTOPRINT_URL}/api/job", headers=headers, json=data)


def send_gcode(commands):
    """ส่งคำสั่ง G-code หลายบรรทัด"""
    data = {"commands": commands}
    return requests.post(
        f"{OCTOPRINT_URL}/api/printer/command", headers=headers, json=data
    )


def check_printer_active():
    """ตรวจสอบสถานะ active จาก OctoPrint continuous print plugin"""
    try:
        resp = requests.get(
            f"{HOST_URL}/plugin/continuousprint/state/get",
            headers={"X-Api-Key": API_KEY},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            active = data.get("active", False)
            print(f"[Printer Status] active={active}")
            return active
        else:
            print(f"[WARN] Printer status check failed ({resp.status_code}): {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Failed to connect to printer API: {e}")
        return False



class ThreeDPrint(Node):
    def __init__(self):
        super().__init__("three_d_print")
        self.create_subscription(Int32, "detection_result", self.cv_callback, 10)
        self.create_subscription(Int32, "test_input", self.test_callback, 10)
        self.create_subscription(Int32, "api_input", self.api_callback, 10)
        self.cv_value = 0
        self.test_value = 0
        self.api_value = 0

    def perform_clear_sequence(self):
        """ทำการ clear_gcode เฉพาะเมื่อ active=True"""
        if check_printer_active():
            self.get_logger().info("Printer active -> executing clear sequence.")
            cancel_job()
            send_gcode(cooldown_gcode)
            time.sleep(900)
            send_gcode(clear_gcode)
            set_active(False)
        else:
            self.get_logger().info("Printer inactive -> skipping clear sequence.")

    def cv_callback(self, msg: Int32):
        self.cv_value = msg.data
        self.get_logger().info(f"[ThreeDPrint] Received CV={msg.data}")
        if self.cv_value == 1:
            self.perform_clear_sequence()

    def test_callback(self, msg: Int32):
        self.test_value = msg.data
        self.get_logger().info(f"[ThreeDPrint] Received Test={msg.data}")
        if self.test_value == 1:
            self.perform_clear_sequence()

    def api_callback(self, msg: Int32):
        self.api_value = msg.data
        self.get_logger().info(f"[ThreeDPrint] Received API={msg.data}")
        if self.api_value == 1:
            self.perform_clear_sequence()


def main(args=None):
    rclpy.init(args=args)
    node = ThreeDPrint()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

