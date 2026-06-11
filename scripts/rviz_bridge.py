#!/usr/bin/env python3
import sys
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from genomstack import RobotIO
from genomstack.rosutils.convert import pose_estimator_to_odometry, rigid_body_to_pose_stamped


class RvizBridge(Node):
    def __init__(self, config_arg: str, rate_hz: float = 20.0):
        super().__init__('genom_rviz_bridge')

        self.io = RobotIO(config_arg, silent=True)

        self.pom_pub = self.create_publisher(Odometry, '/genom/pom/odometry', 10)
        self.mocap_pub = self.create_publisher(Odometry, '/genom/pom_mocap/odometry', 10)
        self.refpoint_pub = self.create_publisher(PoseStamped, '/genom/maneuver/desired', 10)

        self.timer = self.create_timer(1.0 / rate_hz, self.update)

    def update(self):
        try:
            genom_data = self.io.read('pom', 'frame/robot')['frame']
            ros_data = pose_estimator_to_odometry(genom_data, frame_id='map', child_frame_id='body')
            self.pom_pub.publish(ros_data)
        except KeyError:
            pass
        except Exception as e:
            self.get_logger().warn(f'failed to publish pom state: {e}')

        try:
            genom_data = self.io.read('pom_mocap', 'frame/robot')['frame']
            ros_data = pose_estimator_to_odometry(genom_data, frame_id='map', child_frame_id='body')
            self.mocap_pub.publish(ros_data)
        except KeyError:
            pass
        except Exception as e:
            self.get_logger().warn(f'failed to publish pom_mocap state: {e}')
        
        try:
            genom_data = self.io.read('maneuver', 'desired')['desired']
            ros_data = rigid_body_to_pose_stamped(genom_data, frame_id='map')
            self.refpoint_pub.publish(ros_data)
        except KeyError:
            pass
        except Exception as e:
            self.get_logger().warn(f'failed to publish pom state: {e}')


def main():
    if len(sys.argv) not in [2,3]:
        print('usage: python3 ros2/rviz_bridge.py <config name>.yaml [rate_hz]')
        return 1
    config_arg = sys.argv[1]
    
    rate_hz = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0

    rclpy.init()
    node = RvizBridge(config_arg, rate_hz)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
