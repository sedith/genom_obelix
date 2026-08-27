#!/usr/bin/env python3
import sys
from launch import LaunchDescription, LaunchService
from launch.actions import TimerAction
from launch_ros.actions import Node


def make_launch_description(config_dir):
    return LaunchDescription([
        # Node(
        #     package='tf2_ros',
        #     executable='static_transform_publisher',
        #     name='tf_lidar_livox_imu',
        #     arguments=[
        #         '--x', '0.011', '--y', '0.02329', '--z', '-0.04412',
        #         '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
        #         '--frame-id', 'livox_lidar', '--child-frame-id', 'livox_imu',
        #     ],
        #     output='screen',
        # ),
        # Node(
        #     package='livox_ros_driver2',
        #     executable='livox_ros_driver2_node',
        #     name='livox_lidar_publisher',
        #     output='screen',
        #     parameters=[
        #         config_dir + '/mid360.yaml',
        #         {'user_config_path': config_dir + '/mid360.json'}
        #     ],
        # ),
        TimerAction(period=3.0, actions=[
            Node(
                package='mimosa',
                executable='mimosa_node',
                name='mimosa_node',
                output='screen',
                emulate_tty=True,
                parameters=[
                    {'config_path': config_dir + '/mimosa.yaml'},
                ],
                remappings=[
                    ('~/imu/manager/imu_in', '/livox/imu'),
                    ('~/lidar/manager/lidar_in', '/livox/lidar'),
                    ('~/lidar/geometric/map', '/mimosa/local_map'),
                    ('~/graph/odometry', '/mimosa/odometry'),
                    ('~/imu/manager/odometry', '/mimosa/odometry_imufreq'),
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
