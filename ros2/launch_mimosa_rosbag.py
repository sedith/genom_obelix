#!/usr/bin/env python3
import sys
from launch import LaunchDescription, LaunchService
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node


CONFIG_PATH = 'ros2/config/mimosa.yaml'
RVIZ_PATH = 'ros2/config/rviz_livox.rviz'
USE_RVIZ = False


def make_launch_description(bag_path, *args):
    nodes = [
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='tf_lidar_livox_imu',
            arguments=[
                '--x', '0.011', '--y', '0.02329', '--z', '-0.04412',
                '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
                '--frame-id', 'livox_lidar', '--child-frame-id', 'livox_imu',
            ],
            output='screen',
        ),
        Node(
            package='mimosa',
            executable='mimosa_node',
            name='mimosa_node',
            output='screen',
            emulate_tty=True,
            parameters=[
                {'config_path': CONFIG_PATH},
                {'use_sim_time': True},
            ],
            remappings=[
                ('~/imu/manager/imu_in', '/livox/imu'),
                ('~/lidar/manager/lidar_in', '/livox/lidar'),
                ('~/lidar/geometric/map', '/mimosa/local_map'),
                ('~/graph/odometry', '/mimosa/odometry'),
                ('~/imu/manager/odometry', '/mimosa/odometry_imufreq'),
            ],
        ),
        TimerAction(period=3.0, actions=[
            ExecuteProcess(
                cmd=['ros2', 'bag', 'play', bag_path, '--topics', '/tf_static', '/livox/lidar', '/livox/imu', *args],
                output='screen',
            )
        ]),
    ]
    if USE_RVIZ:
        nodes += [
            Node(
                package='rviz2',
                executable='rviz2',
                name='rviz',
                arguments=['-d', RVIZ_PATH],
                parameters=[{'use_sim_time': True}],
                output='screen',
            ),
        ]
    return LaunchDescription(nodes)


def main():
    if len(sys.argv) < 2:
        print('usage: python3 ros2/launch_mimosa_rosbag.py bag_path <args>')
        return 1

    launch_service = LaunchService()
    launch_service.include_launch_description(make_launch_description(sys.argv[1], sys.argv[2:]))
    return launch_service.run()


if __name__ == '__main__':
    raise SystemExit(main())
