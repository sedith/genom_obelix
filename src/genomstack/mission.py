import os
from pathlib import Path
import subprocess
import sys
import numpy as np
from .robot_io import RobotIO
from .utils import is_localhost, quat2yaw


class Mission:
    def __init__(self, io: RobotIO, relative: bool = False):
        self.io = io
        self.relative = relative
        self.bag_process = None

        if self.relative:
            self.set_origin()

    ## log helpers
    def start_logs(self) -> None:
        print('start log')

        ## logs genom
        for c in self.io.components.values():
            c.start_log()

        ## record ros2bag
        # if 'bag' in self.io.cfg.ros2:
        #     subprocess.run(['ssh', self.io.cfg.host, 'rm -r /tmp/genom_obelix/bag'], check=True)
        #     self.bag_process = subprocess.Popen([
        #         sys.executable,
        #         str(self.io.cfg.root / 'ros2/bag_record.py'),
        #         str(self.io.cfg.config_file.name),
        #     ])

    def stop_logs(self) -> None:
        print('stop log')

        ## stop logs
        for c in self.io.components.values():
            c.stop_log()

        ## stop bag record
        if self.bag_process is not None:
            self.bag_process.terminate()
            self.bag_process.wait()
            self.bag_process = None

        ## fetch files
        print(self.io.cfg.log_dir)
        self.io.cfg.log_dir.mkdir(parents=True, exist_ok=True)
        if is_localhost(self.io.cfg.host):
            for f in Path('/tmp/genom_obelix/').glob('*'):
                os.rename(str(f), f'{self.io.cfg.log_dir}/{f.name}')
        else:
            subprocess.run(['scp', '-r', f'{self.io.cfg.host}:/tmp/genom_obelix/*', f'{self.io.cfg.log_dir}'], check=True)
            subprocess.run(['ssh', self.io.cfg.host, 'rm -r /tmp/genom_obelix/*'], check=True)

    ## transform helpers
    def set_origin(self) -> None:
        frame = self.io.read('pom', 'frame/robot')['frame']

        pos = frame['pos']
        att = frame['att']

        self.p0 = np.array([pos['x'], pos['y'], pos['z']], dtype=float)
        self.yaw0 = quat2yaw([att['qw'], att['qx'], att['qy'], att['qz']])

        print(
            f'origin set: '
            f'{self.p0[0]:.3f} {self.p0[1]:.3f} {self.p0[2]:.3f} [m], '
            f'yaw {self.yaw0:.3f} [rad]'
        )

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
        print(f'start spinning and logging')
        self.start_logs()
        self.io.components['rotorcraft'].call('start')

    def start(self, z_start=0.25, ramp_duration=5, prompt=False) -> None:
        _, _, z_start, _ = self.transform_pose(0, 0, z_start, 0)
        print(f'start: {z_start:.3f} [m] -- duration: {ramp_duration} [s]')
        if prompt: input('press enter ...')
        self.io.components['rotorcraft'].call('servo', ack=True)
        self.io.components['maneuver'].call('set_current_state')
        self.io.components['maneuver'].call('take_off', z_start, ramp_duration, ack=True)
        self.io.components['uavpos'].call('servo', ack=True)
        self.io.components['uavatt'].call('servo', ack=True)

    def take_off(self, z=0.6, duration=0, prompt=False) -> None:
        _, _, z, _ = self.transform_pose(0, 0, z, 0)
        print(f'take_off: {z:.3f} [m] -- duration: {duration} [s]')
        if prompt: input('press enter ...')
        self.io.components['maneuver'].call('take_off', z, duration, ack=True)

    def goto(self, x, y, z, yaw, duration=0, prompt=False) -> None:
        x, y, z, yaw = self.transform_pose(x, y, z, yaw)
        print(f'goto: {x:.3f} {y:.3f} {z:.3f} [m] -- {yaw:.3f} [rad] -- duration {duration}s')
        if prompt: input('press enter ...')
        self.io.components['maneuver'].call('goto', x, y, z, yaw, duration, ack=True)

    def land(self, z=0.2, duration=0, prompt=False) -> None:
        _, _, z, _ = self.transform_pose(0, 0, z, 0)
        print(f'land: {z:.3f} [m] -- duration: {duration} [s]')
        if prompt: input('press enter ...')
        self.io.components['maneuver'].call('take_off', z, duration, ack=True)

    def stop(self, prompt=False) -> None:
        input('stop')
        if prompt: input('press enter ...')
        self.io.components['rotorcraft'].call('stop')
        self.stop_logs()
