#!/usr/bin/env python3
import asyncio
import sys
from launch import LaunchDescription, LaunchService
from launch.actions import OpaqueCoroutine, TimerAction
from launch_ros.actions import Node


async def run_gz_livox_for_mimosa():
    import rclpy
    from rclpy.node import Node as RclpyNode
    from sensor_msgs.msg import PointCloud2, PointField
    from sensor_msgs_py import point_cloud2

    class GzLivoxForMimosa(RclpyNode):
        def __init__(self):
            super().__init__('gz_livox_for_mimosa')
            self.sub = self.create_subscription(PointCloud2, '/livox/lidar', self.callback, 10)
            self.pub = self.create_publisher(PointCloud2, '/livox/lidar_mimosa', 10)
            self.printed_fields = False

        def callback(self, msg: PointCloud2):
            input_fields = [field.name for field in msg.fields]
            if not self.printed_fields:
                self.printed_fields = True
                self.get_logger().info(f'converting point fields for Mimosa: {input_fields}')

            field_names = [name for name in ('x', 'y', 'z', 'intensity') if name in input_fields]
            if not {'x', 'y', 'z'}.issubset(field_names):
                self.get_logger().warn(f'cannot convert cloud without x/y/z fields: {input_fields}')
                return

            points = []
            for point in point_cloud2.read_points(msg, field_names=field_names, skip_nans=True):
                x = float(point[0])
                y = float(point[1])
                z = float(point[2])
                intensity = float(point[3]) if 'intensity' in field_names else 0.0
                points.append((x, y, z, 0, intensity, 0, 0))

            fields = [
                PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
                PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
                PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
                PointField(name='t', offset=12, datatype=PointField.UINT32, count=1),
                PointField(name='intensity', offset=16, datatype=PointField.FLOAT32, count=1),
                PointField(name='tag', offset=20, datatype=PointField.UINT8, count=1),
                PointField(name='line', offset=21, datatype=PointField.UINT8, count=1),
            ]
            self.pub.publish(point_cloud2.create_cloud(msg.header, fields, points))

    rclpy.init(args=None)
    node = GzLivoxForMimosa()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            await asyncio.sleep(0.01)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def make_launch_description(config_dir):
    return LaunchDescription([
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='gz_sensor_bridge',
            output='screen',
            arguments=[
                '/livox/lidar/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
                '/livox/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
            ],
            remappings=[
                ('/livox/lidar/points', '/livox/lidar'),
            ]
        ),
        OpaqueCoroutine(coroutine=run_gz_livox_for_mimosa, ignore_context=True),
        TimerAction(period=3.0, actions=[
            Node(
                package='mimosa',
                executable='mimosa_node',
                name='mimosa_node',
                output='screen',
                emulate_tty=True,
                parameters=[
                    {'config_path': config_dir + '/mimosa_gz.yaml'},
                ],
                remappings=[
                    ('~/imu/manager/imu_in', '/livox/imu'),
                    ('~/lidar/manager/lidar_in', '/livox/lidar_mimosa'),
                    ('~/graph/odometry', '/mimosa/odometry'),
                    ('~/lidar/geometric/map', '/mimosa/local_map'),
                ],
            )]
        ),
    ])


def main():
    launch_service = LaunchService()
    launch_service.include_launch_description(make_launch_description(sys.argv[1]))
    return launch_service.run()


if __name__ == '__main__':
    raise SystemExit(main())
