#!/usr/bin/env python3
import sys
from genomstack import LocalRunner, Config


def main():
    config_arg = 'tilthex'
    cfg = Config(config_arg)

    if not cfg.ros2.enabled:
        print('ros2 disabled')
        return 0

    runner = LocalRunner(workspace=str(cfg.root), setup=cfg.setup)

    try:
        for launchfile in cfg.ros2.launchfiles:
            cmds = [
                'export ROS_LOCALHOST_ONLY=0',
                f'export ROS_DOMAIN_ID={cfg.ros2.domain_id}',
                f'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp',
                f'export CYCLONEDDS_URI=file:///home/onepiece/mjacquet/genom_obelix/ros2/config/cyclonedds.xml',
                f'python3 ros2/{launchfile} {cfg.root}/ros2/config/'
            ]
            runner.start('ros2', cmds)

        for name, sidecar in cfg.sidecars.items():
            cmds = [
                'export ROS_LOCALHOST_ONLY=0',
                f'export ROS_DOMAIN_ID={cfg.ros2.domain_id}',
                f'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp',
                f'export CYCLONEDDS_URI=file:///home/onepiece/mjacquet/genom_obelix/ros2/config/cyclonedds.xml',
                sidecar
            ]
            runner.start(name, cmds, wait=0.5)

        runner.hang()

    except KeyboardInterrupt:
        print('stopping')
        runner.stop_all()
    except Exception as e:
        print(f'error: {e}')
        print('killing')
    finally:
        runner.kill_all()


if __name__ == '__main__':
    raise SystemExit(main())
