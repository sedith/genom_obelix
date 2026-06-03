#!/usr/bin/env python3
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import Odometry
from genomstack import RobotIO
from genomstack.rosutils.convert import odom_to_pose_estimator, Cov


class LioRelay(Node):
    def __init__(self, config_arg: str):
        super().__init__('lio_relay')

        self.io = RobotIO(config_arg, silent=True)

        self.topic = '/rko_lio/odometry'
        self.publisher_name = 'lidar'
        self.repub_vel = True
        self.printed = False
        self.cov = Cov().from_stds(std_p=0.001, std_eul=0.1, std_v=0.1, std_w=0.1)

        self.create_subscription(Odometry, self.topic, self.callback, 10)

    def callback(self, msg: Odometry):
        if not self.printed:
            self.printed = True
            p = msg.pose.pose.position
            self.get_logger().info(f'first pose retrieved: {p.x:.3f}, {p.y:.3f}, {p.z:.3f}')
        ts = divmod(time.time_ns(), 1_000_000_000)
        data = odom_to_pose_estimator(msg, ts=ts, cov=self.cov, repub_vel=self.repub_vel)
        self.io.publish(self.publisher_name, data)


def main():
    if len(sys.argv) != 2:
        print('usage: python3 ros2/lio_relay.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]

    rclpy.init()
    node = LioRelay(config_arg)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
