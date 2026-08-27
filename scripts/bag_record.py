#!/usr/bin/env python3
import os
import sys
from genomstack.config import Config
from genomstack.process import host_path
import time


def main():
    if len(sys.argv) != 2:
        print('usage: python3 scripts/bag_record.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]

    cfg = Config(config_arg)

    if not cfg.ros2.enabled:
        print('ros2 disabled')
        return 0

    if 'bag' not in cfg.ros2 or not cfg.ros2.bag:
        print('ros2 bag disabled')
        return 0

    path = host_path(cfg.tmp_path / f'bag_{time.strftime("%y%m%d_%H%M%S")}', 'localhost')

    cmd = [
        'ros2',
        'bag',
        'record',
        '-o',
        path,
        *cfg.ros2.bag,
    ]
    os.execvp(cmd[0], cmd)


if __name__ == '__main__':
    raise SystemExit(main())
