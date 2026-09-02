#!/usr/bin/env python3
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from rclpy.qos import qos_profile_sensor_data

from rclpy.qos import (
    QoSProfile,
    QoSHistoryPolicy,
    QoSReliabilityPolicy,
    QoSDurabilityPolicy,
)

class Monitor(Node):
    def __init__(self):
        super().__init__('imu_monitor')
        self.last = None

        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )

        self.create_subscription(
            Imu,
            '/livox/imu',
            self.cb,
            qos,
        )


    def cb(self, msg):
        now = time.monotonic_ns()

        if self.last is not None:
            dt_ms = (now - self.last) / 1e6
            if dt_ms > 10:
                print(f"*** IMU RECEIVE GAP: {dt_ms:.3f} ms", flush=True)

        self.last = now

rclpy.init()
rclpy.spin(Monitor())
