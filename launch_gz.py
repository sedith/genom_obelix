#!/usr/bin/env python3
import sys
from genomstack import LocalRunner, Config


def main():
    if len(sys.argv) != 2:
        print('usage: python3 launch_ros2.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]

    cfg = Config(config_arg)
    runner = LocalRunner(workspace=str(cfg.root / 'gz'), setup=cfg.setup)

    try:
        runner.start('gz', [f'gz sim {cfg.gz.options} {cfg.gz.world}'])
        runner.hang()
    except KeyboardInterrupt:
        print('stopping')
        runner.stop_all()
    except Exception as e:
        print(f'error: {e}')
        print('killing')
        runner.kill_all()


if __name__ == '__main__':
    raise SystemExit(main())
