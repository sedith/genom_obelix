import os
import shlex
import subprocess
import numpy as np
from .process import LocalRunner, RemoteTmuxRunner, is_localhost, shell_path
from .robot_io import RobotIO
from .utils import quat2yaw


class Mission:
    def __init__(self, io: RobotIO, relative: bool = False, rosbag: bool = False):
        self.io = io
        self.relative = relative
        self.rosbag = rosbag
        if rosbag and self.io.cfg.ros2.enabled:
            if is_localhost(self.io.cfg.host):
                self.bag_runner = LocalRunner(workspace=self.io.cfg.root, setup=self.io.cfg.setup)
            else:
                self.bag_runner = RemoteTmuxRunner(host=self.io.cfg.host, workspace=self.io.cfg.workspace, setup=self.io.cfg.setup, session='genomstack_rosbag')
        else:
            self.bag_runner = None
        self.logging = False

        if self.relative:
            self.set_origin()

    ## log helpers
    def start_logs(self) -> None:
        if self.logging:
            return
        print('start log')

        ## logs genom
        for c in self.io.components.values():
            c.start_log()

        if self.bag_runner is not None:
            self.bag_runner.stop_all(timeout=1.0)
            bag_dir = self.io.cfg.tmp_path / 'bag'
            commands = [
                f'rm -rf {shell_path(bag_dir, expand=is_localhost(self.io.cfg.host))}',
                'export ROS_LOCALHOST_ONLY=0',
                f'export ROS_DOMAIN_ID={self.io.cfg.ros2.domain_id}',
                f'python3 scripts/bag_record.py {shlex.quote(self.io.cfg.config_file.name)}',
            ]

            self.bag_runner.start(
                'rosbag',
                commands,
                wait=2.0,
            )

        self.logging = True

    def stop_logs(self) -> None:
        if not self.logging:
            return
        print('stop log')

        ## stop logs
        for c in self.io.components.values():
            c.stop_log()

        if self.bag_runner:
            self.bag_runner.stop_all(timeout=1.0)

        self.logging = False

    def export_logs(self) -> None:
        self.io.cfg.log_dir.mkdir(parents=True, exist_ok=True)
        if is_localhost(self.io.cfg.host):
            for f in self.io.cfg.tmp_path.expanduser().glob('*'):
                os.rename(str(f), f'{self.io.cfg.log_dir}/{f.name}')
        else:
            subprocess.run(['scp', '-r', f'{self.io.cfg.host}:{self.io.cfg.tmp_path}/*', f'{self.io.cfg.log_dir}'], check=True)
            subprocess.run(['ssh', self.io.cfg.host, f'rm -r {shell_path(self.io.cfg.tmp_path)}/*'], check=True)

    ## transform helpers
    def set_origin(self) -> None:
        frame = self.io.read('pom', 'frame/robot')['frame']
        pos = frame['pos']
        att = frame['att']
        self.p0 = np.array([pos['x'], pos['y'], pos['z']], dtype=float)
        self.yaw0 = quat2yaw([att['qw'], att['qx'], att['qy'], att['qz']])
        print(f'origin set: {self.p0[0]:.3f} {self.p0[1]:.3f} {self.p0[2]:.3f} [m],  yaw {self.yaw0:.3f} [rad]')

    def transform_pose(self, x, y, z, yaw):
        if not self.relative:
            return x, y, z, yaw
        c = np.cos(self.yaw0)
        s = np.sin(self.yaw0)
        p = self.p0 + np.array([
            c * x - s * y,
            s * x + c * y,
            z,
        ])
        return (*p, self.yaw0 + yaw)

    ## mission helpers
    def spin(self) -> None:
        print(f'- start spinning and logging')
        if 'phynt' in self.io.components:
            self.io.components['phynt'].call('set_wo_zero', 1)
        self.io.components['rotorcraft'].call('start')

    def start(self, z_start=0.25, ramp_duration=5, prompt=False) -> None:
        _, _, z_start, _ = self.transform_pose(0, 0, z_start, 0)
        print(f'- start: {z_start:.3f} [m] -- duration: {ramp_duration} [s]')
        if prompt: input('  | press enter ...')
        self.io.components['rotorcraft'].call('servo', ack=True)
        self.io.components['maneuver'].call('set_current_state')
        if 'phynt' in self.io.components:
            self.io.components['phynt'].call('stop', ack=True)
            self.io.components['phynt'].call('set_current_position')
            self.io.components['phynt'].call('servo', ack=True)
        self.io.components['maneuver'].call('take_off', z_start, ramp_duration, ack=True)
        self.io.components['uavpos'].call('servo', ack=True)
        self.io.components['uavatt'].call('servo', ack=True)
        
    def goto(self, x, y, z, yaw, duration=0, prompt=False) -> None:
        x, y, z, yaw = self.transform_pose(x, y, z, yaw)
        print(f'- goto: {x:.3f} {y:.3f} {z:.3f} [m] -- {yaw:.3f} [rad] -- duration {duration}s')
        if prompt: input('  | press enter ...')
        self.io.components['maneuver'].call('goto', x, y, z, yaw, duration, ack=True)

    def gotoz(self, z=0.2, duration=0, prompt=False) -> None:
        _, _, z, _ = self.transform_pose(0, 0, z, 0)
        print(f'- goto z: {z:.3f} [m] -- duration: {duration} [s]')
        if prompt: input('  | press enter ...')
        self.io.components['maneuver'].call('take_off', z, duration, ack=True)

    def stop(self, prompt=False) -> None:
        print('- stop')
        if prompt: input('  | press enter ...')
        self.stop_logs()
        self.io.components['rotorcraft'].call('stop')
        self.export_logs()
