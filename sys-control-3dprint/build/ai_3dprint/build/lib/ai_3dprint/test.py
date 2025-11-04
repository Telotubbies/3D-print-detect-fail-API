#!/usr/bin/env python3
# ai_3dprint/test.py

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class TestInput(Node):
    def __init__(self):
        super().__init__("test_input")
        self.publisher_ = self.create_publisher(Int32, "test_input", 10)

    def run(self):
        while rclpy.ok():
            try:
                user_input = input("Enter test value (0 or 1): ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if user_input in ["0", "1"]:
                msg = Int32()
                msg.data = int(user_input)
                self.publisher_.publish(msg)
                self.get_logger().info(f"[Test] Published value = {msg.data}")
            else:
                print("Invalid input. Please enter 0 or 1.")


def main(args=None):
    rclpy.init(args=args)
    node = TestInput()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
