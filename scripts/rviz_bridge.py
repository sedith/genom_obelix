#!/usr/bin/env python3
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray
from genomstack import RobotIO
from genomstack.rosutils.convert import pose_estimator_to_odometry, rigid_body_to_pose_stamped
from genomstack.utils import euler2quat


def parse_sdf_visual_markers(sdf_file, frame_id='body'):
    markers = []
    root = ET.parse(sdf_file).getroot()

    for i, visual in enumerate(root.findall('.//visual')):
        marker = Marker()
        marker.header.frame_id = frame_id
        marker.ns = 'robot_model'
        marker.id = i
        marker.action = Marker.ADD

        marker.pose.orientation.w = 1.0

        pose = visual.find('pose')
        if pose is not None:
            x, y, z, r, p, yaw = map(float, pose.text.split())
            marker.pose.position.x = x
            marker.pose.position.y = y
            marker.pose.position.z = z
            q = euler2quat([r, p, yaw])
            marker.pose.orientation.w = q[0]
            marker.pose.orientation.x = q[1]
            marker.pose.orientation.y = q[2]
            marker.pose.orientation.z = q[3]

        geom = visual.find('geometry')
        if geom is None:
            continue
        if geom.find('cylinder') is not None:
            cyl = geom.find('cylinder')
            radius = float(cyl.find('radius').text)
            length = float(cyl.find('length').text)

            marker.type = Marker.CYLINDER
            marker.scale.x = 2 * radius
            marker.scale.y = 2 * radius
            marker.scale.z = length
        elif geom.find('box') is not None:
            box = geom.find('box')
            sx, sy, sz = map(float, box.find('size').text.split())

            marker.type = Marker.CUBE
            marker.scale.x = sx
            marker.scale.y = sy
            marker.scale.z = sz
        elif geom.find('sphere') is not None:
            sphere = geom.find('sphere')
            radius = float(sphere.find('radius').text)

            marker.type = Marker.SPHERE
            marker.scale.x = 2 * radius
            marker.scale.y = 2 * radius
            marker.scale.z = 2 * radius
        else:
            continue

        diffuse = visual.find('material/diffuse')
        if diffuse is not None:
            r, g, b, a = map(float, diffuse.text.split())
            marker.color.r = r
            marker.color.g = g
            marker.color.b = b
            marker.color.a = a
        else:
            marker.color.r = 0.5
            marker.color.g = 0.5
            marker.color.b = 0.5
            marker.color.a = 1.0

        markers.append(marker)

    return markers


class RvizBridge(Node):
    def __init__(self, config_arg: str, rate_hz: float = 20.0):
        super().__init__('genom_rviz_bridge')

        self.io = RobotIO(config_arg, silent=True)

        self.pom_pub = self.create_publisher(Odometry, '/genom/pom/odometry', 10)
        self.mocap_pub = self.create_publisher(Odometry, '/genom/pom_mocap/odometry', 10)
        self.refpoint_pub = self.create_publisher(PoseStamped, '/genom/maneuver/desired', 10)

        self.model_pub = self.create_publisher(MarkerArray, '/genom/robot_model', 10)
        sdf_file = Path('gz/mrsim-tilthex/model.sdf')
        self.model_markers = parse_sdf_visual_markers(sdf_file, frame_id='body')

        self.timer = self.create_timer(1.0 / rate_hz, self.update)

    def update(self):
        msg = MarkerArray()
        for marker in self.model_markers:
            msg.markers.append(marker)
        self.model_pub.publish(msg)

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
