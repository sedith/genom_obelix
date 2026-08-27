#!/usr/bin/env python3
import sys
from genomstack import LocalRunner, Config


def main():
    if len(sys.argv) != 2:
        print('usage: python3 launch_rviz.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]
    
    cfg = Config(config_arg)
    runner = LocalRunner(workspace=cfg.root, setup=cfg.setup)

    try:
        cmds = [
            'export ROS_LOCALHOST_ONLY=0',
            f'export ROS_DOMAIN_ID={cfg.ros2.domain_id}',
            'rviz2 -d ros2/config/rviz_livox.rviz'
        ]
        runner.start('rviz', cmds)

        print('hanging until ^C...')
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
