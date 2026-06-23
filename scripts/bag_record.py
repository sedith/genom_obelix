#!/usr/bin/env python3
import os
import sys

from genomstack.config import Config


def main():
    if len(sys.argv) != 2:
        print('usage: python3 scripts/bag_record.py <config name>.yaml')
        return 1

    cfg = Config(sys.argv[1])

    if not cfg.ros2.enabled:
        print('ros2 disabled')
        return 0

    if 'bag' not in cfg.ros2 or not cfg.ros2.bag:
        print('ros2 bag disabled')
        return 0

    bag_dir = cfg.tmp_path / 'bag'
    os.makedirs(cfg.tmp_path, exist_ok=True)

    cmd = [
        'ros2',
        'bag',
        'record',
        '-o',
        str(bag_dir),
        *cfg.ros2.bag,
    ]
    os.execvp(cmd[0], cmd)


if __name__ == '__main__':
    raise SystemExit(main())
