#!/usr/bin/env python3
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from genomstack import RobotIO
from genomstack.rosutils.convert import odom_to_pose_estimator, Cov


class LioRelay(Node):
    def __init__(self, config_arg: str, topic: str):
        super().__init__('lio_relay')

        self.io = RobotIO(config_arg, silent=True)

        ## arguments
        self.topic = topic
        self.publisher_name = 'lidar'
        self.repub_vel = True
        self.min_rate = 9.0

        self.printed = False
        self.last_msg_time = None
        self.last_warn_time = 0.0
        self.cov = Cov().from_stds(std_p=0.001, std_eul=0.01, std_v=0.02, std_w=0.02)

        self.create_subscription(Odometry, self.topic, self.callback, 10)
        self.create_timer(1.0, self.check_rate)

    def callback(self, msg: Odometry):
        self.last_msg_time = time.monotonic()

        if not self.printed:
            self.printed = True
            p = msg.pose.pose.position
            self.get_logger().info(f'first pose retrieved: {p.x:.3f}, {p.y:.3f}, {p.z:.3f}')
        ts = divmod(time.time_ns(), 1_000_000_000)
        data = odom_to_pose_estimator(msg, ts=ts, cov=self.cov, repub_vel=self.repub_vel)
        self.io.publish(self.publisher_name, data)

    def check_rate(self):
        if self.last_msg_time is not None:
            now = time.monotonic()
            if now - self.last_msg_time > 1.0 / self.min_rate and now - self.last_warn_time > 2.0:
                self.last_warn_time = now
                self.get_logger().warn(f'{self.topic} rate below {self.min_rate:.1f} Hz')


def main():
    if len(sys.argv) != 3:
        print('usage: python3 ros2/lio_relay.py <config name>.yaml topic')
        return 1
    config_arg = sys.argv[1]
    topic = sys.argv[2]

    rclpy.init()
    node = LioRelay(config_arg, topic)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
