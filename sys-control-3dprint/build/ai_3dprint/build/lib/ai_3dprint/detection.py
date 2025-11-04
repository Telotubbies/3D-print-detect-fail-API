#!/usr/bin/env python3
# ai_3dprint/detection.py

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
import cv2

#try:
#    from ultralytics import YOLO
#    _HAS_YOLO = True
#except Exception:
#    _HAS_YOLO = False
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory
import os

class DetectionNode(Node):
    def __init__(self):
        super().__init__("detection_node")

        # ✅ หา path ของโมเดลภายใน package
        package_share = get_package_share_directory('ai_3dprint')
        model_path = os.path.join(package_share, 'models', 'best.pt')

        # ตรวจสอบว่าไฟล์มีอยู่จริงหรือไม่
        if not os.path.exists(model_path):
            self.get_logger().error(f"Model file not found: {model_path}")
        else:
            self.get_logger().info(f"Loading model from: {model_path}")

        # โหลดโมเดล YOLO
        self.model = YOLO(model_path)

        self.publisher_ = self.create_publisher(Int32, "detection_result", 10)
        self.timer = self.create_timer(10.0, self.timer_callback)

#        if _HAS_YOLO:
#            try:
#                self.model = YOLO('best.pt')
#            except Exception as e:
#                self.get_logger().error(f"Failed to load model best.pt: {e}")
#                self.model = None
#        else:
#            self.model = None
#            self.get_logger().warning("YOLO not available → detection disabled")

        self.class_names = ["normal print", "printer head", "spaghettis"]

    def timer_callback(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.get_logger().error("Cannot open camera")
            return

        ret, frame = cap.read()
        cap.release()

        if not ret:
            self.get_logger().error("Failed to capture frame")
            return

        detected_spaghetti = False
        if self.model:
            try:
                results = self.model(frame)
                detections = results[0].boxes
                classes = detections.cls.tolist() if hasattr(detections, "cls") else []
                for cls_id in classes:
                    if 0 <= int(cls_id) < len(self.class_names):
                        if self.class_names[int(cls_id)] == "spaghettis":
                            detected_spaghetti = True
                            break
            except Exception as e:
                self.get_logger().error(f"Inference error: {e}")

        msg = Int32()
        msg.data = 1 if detected_spaghetti else 0
        self.publisher_.publish(msg)
        self.get_logger().info(f"[Detection] Published CV={msg.data}")


def main(args=None):
    rclpy.init(args=args)
    node = DetectionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
