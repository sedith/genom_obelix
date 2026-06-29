#!/usr/bin/env python3
import shlex
import sys
from genomstack import LocalRunner, Config


def gz_cmd(*args):
    return 'gz sim ' + ' '.join(shlex.quote(str(arg)) for arg in args if arg)


def main():
    if len(sys.argv) != 2:
        print('usage: python3 launch_gz.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]

    cfg = Config(config_arg)
    runner = LocalRunner(workspace=str(cfg.root / 'gz'), setup=cfg.setup)
    options = shlex.split(cfg.gz.options)

    try:
        if '-s' in options:
            runner.start('gz-server', [gz_cmd(*options, cfg.gz.world)])
        else:
            runner.start('gz-server', [gz_cmd('-s', *options, cfg.gz.world)])
            runner.start('gz-gui', [gz_cmd('-g')])
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
