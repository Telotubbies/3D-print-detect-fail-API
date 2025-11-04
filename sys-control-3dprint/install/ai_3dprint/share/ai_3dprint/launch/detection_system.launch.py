#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package="ai_3dprint",
            executable="detection",
            output="screen"
        ),
        Node(
            package="ai_3dprint",
            executable="test",
            output="screen"
        ),
        Node(
            package="ai_3dprint",
            executable="three_d_print",
            output="screen"
        ),
    ])
