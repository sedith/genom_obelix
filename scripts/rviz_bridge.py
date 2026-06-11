#!/usr/bin/env python3
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray
from genomstack import RobotIO
from genomstack.rosutils.convert import pose_estimator_to_odometry, rigid_body_to_pose_stamped
from genomstack.utils import euler2quat, euler2rot, rot2euler


def parse_pose(elem):
    if elem is None or elem.text is None:
        return np.zeros(3), np.eye(3)
    x, y, z, r, p, yaw = map(float, elem.text.split())
    return np.array([x, y, z]), euler2rot([r, p, yaw])


def compose_pose(parent, child):
    parent_xyz, parent_rot = parent
    child_xyz, child_rot = child
    return parent_xyz + parent_rot @ child_xyz, parent_rot @ child_rot


def model_sdf_path(world_file, uri):
    if not uri.startswith('model://'):
        return None
    return world_file.parent / uri.removeprefix('model://') / 'model.sdf'


def parse_sdf_visual_markers(world_file, model_name, frame_id='body'):
    world_file = Path(world_file)
    world_root = ET.parse(world_file).getroot()
    model = world_root.find(f'.//world/model[@name="{model_name}"]')
    if model is None:
        for candidate in world_root.findall('.//world/model'):
            for include in candidate.findall('include'):
                uri = include.findtext('uri', '')
                name = include.findtext('name', '')
                if uri == f'model://{model_name}' or name == model_name:
                    model = candidate
                    break
            if model is not None:
                break
    if model is None:
        return []

    markers = []

    def add_visuals_from_model(sdf_file, base_pose):
        root = ET.parse(sdf_file).getroot()

        for link in root.findall('.//model/link'):
            link_pose = compose_pose(base_pose, parse_pose(link.find('pose')))
            for visual in link.findall('visual'):
                marker = marker_from_visual(visual, link_pose, len(markers), frame_id)
                if marker is not None:
                    markers.append(marker)

        for include in root.findall('.//model/include'):
            uri = include.findtext('uri', '')
            include_sdf = model_sdf_path(world_file, uri)
            if include_sdf is not None and include_sdf.exists():
                add_visuals_from_model(include_sdf, compose_pose(base_pose, parse_pose(include.find('pose'))))

    def marker_from_visual(visual, base_pose, marker_id, frame_id):
        geom = visual.find('geometry')
        if geom is None:
            return None

        marker = Marker()
        marker.header.frame_id = frame_id
        marker.ns = 'robot_model'
        marker.id = marker_id
        marker.action = Marker.ADD

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
            return None

        xyz, rot = compose_pose(base_pose, parse_pose(visual.find('pose')))
        marker.pose.position.x = float(xyz[0])
        marker.pose.position.y = float(xyz[1])
        marker.pose.position.z = float(xyz[2])
        q = euler2quat(rot2euler(rot))
        marker.pose.orientation.w = q[0]
        marker.pose.orientation.x = q[1]
        marker.pose.orientation.y = q[2]
        marker.pose.orientation.z = q[3]

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

        return marker

    for include in model.findall('include'):
        uri = include.findtext('uri', '')
        sdf_file = model_sdf_path(world_file, uri)
        if sdf_file is not None and sdf_file.exists():
            add_visuals_from_model(sdf_file, parse_pose(include.find('pose')))

    return markers


class RvizBridge(Node):
    def __init__(self, config_arg: str, rate_hz: float = 20.0):
        super().__init__('genom_rviz_bridge')

        self.io = RobotIO(config_arg, silent=True)

        self.pom_pub = self.create_publisher(Odometry, '/genom/pom/odometry', 10)
        self.mocap_pub = self.create_publisher(Odometry, '/genom/pom_mocap/odometry', 10)
        self.ref_man_pub = self.create_publisher(PoseStamped, '/genom/maneuver/desired', 10)
        self.ref_phynt_pub = self.create_publisher(PoseStamped, '/genom/phynt/desired', 10)

        self.model_pub = self.create_publisher(MarkerArray, '/genom/robot_model', 10)
        world_file = self.io.cfg.root / 'gz' / self.io.cfg.gz.world
        self.model_markers = parse_sdf_visual_markers(world_file, 'TX', frame_id='body')

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
            self.ref_man_pub.publish(ros_data)
        except KeyError:
            pass
        except Exception as e:
            self.get_logger().warn(f'failed to publish maneuver ref: {e}')

        try:
            genom_data = self.io.read('phynt', 'desired')['desired']
            ros_data = rigid_body_to_pose_stamped(genom_data, frame_id='map')
            self.ref_phynt_pub.publish(ros_data)
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
