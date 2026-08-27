#!/usr/bin/env python3
import sys
from genomstack import LocalRunner, Config


def main():
    config_arg = 'tilthex_bridge'
    cfg = Config(config_arg)

    cfg.tmp_path.expanduser().mkdir(parents=True, exist_ok=True)
    runner = LocalRunner(workspace=cfg.root, setup=cfg.setup)
    delay = 0.1

    try:
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


if __name__ == '__main__':
    raise SystemExit(main())
