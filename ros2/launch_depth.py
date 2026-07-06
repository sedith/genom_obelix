#!/usr/bin/env python3
import sys
from launch import LaunchDescription, LaunchService
from launch_ros.actions import Node


def make_launch_description(config_dir=None):
    return LaunchDescription([
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='gz_depth_bridge',
            output='screen',
            arguments=[
                '/camera/color/image@sensor_msgs/msg/Image[gz.msgs.Image',
                '/camera/depth/image@sensor_msgs/msg/Image[gz.msgs.Image',
            ],
        ),
    ])


def main():
    launch_service = LaunchService()
    config_dir = sys.argv[1] if len(sys.argv) > 1 else None
    launch_service.include_launch_description(make_launch_description(config_dir))
    return launch_service.run()


if __name__ == '__main__':
    raise SystemExit(main())
