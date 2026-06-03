#!/usr/bin/env python3

import os
import shlex
import sys
from pathlib import Path
from genomstack.config import Config
from genomstack.utils import is_localhost

# REMOTE_ENV = 'GENOMSTACK_BAG_REMOTE_EXEC'
SOURCED_ENV = 'GENOMSTACK_ROS2_SOURCED'


## relaunchers
def relaunch_remote(cfg: Config, config_arg: str) -> None:
    remote_cmd = (
        f'source ~/.onepiece.bashrc && '
        f'cd {cfg.workspace} && '
        # f'export {REMOTE_ENV}=1 && '
        f'exec python3 ros2/bag_record.py {shlex.quote(config_arg)}'
    )

    os.execvp('ssh', [
        'ssh',
        '-t',
        cfg.host,
        f'bash -lc {shlex.quote(remote_cmd)}',
    ])


def relaunch_with_ros_env(cfg: Config) -> None:
    setup_cmds = []
    for setup in cfg.ros2.setup:
        setup = os.path.expandvars(os.path.expanduser(setup))
        setup_path = Path(setup)
        if not setup_path.is_absolute():
            setup_path = cfg.root / setup_path

        setup_cmds.append(f'source {shlex.quote(str(setup_path))}')

    env_cmds = [
        f'export {SOURCED_ENV}=1',
        'export ROS_LOCALHOST_ONLY=0',
    ]

    if 'domain_id' in cfg.ros2:
        env_cmds.append(
            f'export ROS_DOMAIN_ID={shlex.quote(str(cfg.ros2.domain_id))}'
        )

    cmd = ' && '.join(setup_cmds + env_cmds)
    cmd += ' && exec ' + ' '.join(
        shlex.quote(arg) for arg in [sys.executable] + sys.argv
    )

    os.execv('/bin/bash', ['bash', '-lc', cmd])



def main():
    if len(sys.argv) != 2:
        print('usage: python3 ros2/bag_record.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]
    
    cfg = Config(config_arg)

    if not cfg.ros2.enabled:
        print('ros2 disabled')
        return 0

    if not cfg.ros2.bag:
        print('ros2 bag disabled')
        return 0

    ## relaunch script if necessary
    if not is_localhost(cfg.host):# and os.environ.get(REMOTE_ENV) != '1':
        relaunch_remote(cfg, config_arg)

    if os.environ.get(SOURCED_ENV) != '1':
        relaunch_with_ros_env(cfg)

    cmd = [
        'ros2',
        'bag',
        'record',
        '-o',
        '/tmp/genom_obelix/bag',
        *cfg.ros2.bag,
    ]

    os.execvp(cmd[0], cmd)


if __name__ == '__main__':
    raise SystemExit(main())
