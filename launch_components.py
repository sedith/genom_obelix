#!/usr/bin/env python3
import sys
from genomstack import LocalRunner, Config


def main():
    if len(sys.argv) != 2:
        print('usage: python3 launch_ros2.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]
    
    cfg = Config(config_arg)
    runner = LocalRunner(workspace=cfg.root, setup=cfg.setup)
    delay = 0.5

    try:
        runner.run('h2 end', check=False)
        runner.run('h2 init', check=False, wait=delay)
        runner.start('genomixd', 'genomixd', wait=delay)

        for name, component in cfg.components.items():
            runner.start(name, f'{component.type}-pocolibs -f -i {name}', wait=delay)

        for name, sidecar in cfg.sidecars.items():
            cmds = [
                'export ROS_LOCALHOST_ONLY=0',
                f'export ROS_DOMAIN_ID={cfg.ros2.domain_id}',
                sidecar
            ]
            runner.start(name, cmds, wait=delay)

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
        runner.run('h2 end', check=False)
        runner.run(f'rm ~/.*.pid-*', check=False)


if __name__ == '__main__':
    raise SystemExit(main())
