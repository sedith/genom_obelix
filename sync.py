#!/usr/bin/env python3
import subprocess
import sys
import shlex
from genomstack.config import Config
from genomstack.process import is_localhost


def rsync_excludes(root):
    excludes = ['.git/', 'logs/']
    gitignore = root / '.gitignore'
    with open(gitignore, 'r') as f:
        excludes += [
            line.strip()
            for line in f
            if line.strip() and not line.lstrip().startswith('#')
        ]
    return excludes


def main():
    if len(sys.argv) != 2:
        print('usage: python3 sync.py <config name>.yaml')
        return 1
    cfg = Config(sys.argv[1])

    if is_localhost(cfg.host):
        print(f'{cfg.host} is local; nothing to sync')
        return 0

    if not hasattr(cfg, 'workspace'):
        print(f'error: config {cfg.config_file} has no "workspace" field')
        return 1

    src = str(cfg.root) + '/'
    dst = f'{cfg.host}:{cfg.workspace.rstrip("/")}/'

    subprocess.run(
        ['ssh', cfg.host, f'mkdir -p {shlex.quote(cfg.workspace)}'],
        check=True,
    )

    cmd = ['rsync', '-az', '--delete']
    for pattern in rsync_excludes(cfg.root):
        cmd += ['--exclude', pattern]
    cmd += [src, dst]

    print(f'syncing {src} -> {dst}')
    subprocess.run(cmd, check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
