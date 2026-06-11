#!/usr/bin/env python3
import sys
from launch import LaunchDescription, LaunchService
from launch.actions import TimerAction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def make_launch_description(config_dir):
    return LaunchDescription([
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='tf_lidar_livox_imu',
            arguments=[
                '--x', '0.011', '--y', '0.02329', '--z', '-0.04412',
                '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
                '--frame-id', 'TX/livox/base/livox_lidar', '--child-frame-id', 'TX/livox/base/livox_imu',
            ],
            output='screen',
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='tf_rko',
            arguments=[
                '--x', '0', '--y', '0', '--z', '0',
                '--roll', '0', '--pitch', '0', '--yaw', '0',
                '--frame-id', 'body_rko', '--child-frame-id', 'TX/livox/base/livox_lidar',
            ],
            output='screen',
        ),
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
        TimerAction(period=3.0, actions=[
            Node(
                package='rko_lio',
                executable='online_node',
                name='rko_lio',
                output='screen',
                emulate_tty=True,
                parameters=[
                    config_dir + '/rko_lio_gz.yaml',
                ]
            )]
        ),
    ])


def main():
    launch_service = LaunchService()
    launch_service.include_launch_description(make_launch_description(sys.argv[1]))
    return launch_service.run()


if __name__ == '__main__':
    raise SystemExit(main())
