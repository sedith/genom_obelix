#!/usr/bin/env python3
import sys
import time
import numpy as np
from genomstack import RobotIO, Mission
from genomstack.utils import quat2euler, quat2yaw


p_ee_b = np.array([0.476, 0.275, 0.03])
yaw_ee_b = np.pi/6

def ee_to_body(x, y, z, yaw):
    yaw_body = yaw - yaw_ee_b

    c = np.cos(yaw_body)
    s = np.sin(yaw_body)

    p_body = np.array([x, y, z]) - np.array([
        c * p_ee_b[0] - s * p_ee_b[1],
        s * p_ee_b[0] + c * p_ee_b[1],
        p_ee_b[2],
    ])

    return (*p_body, yaw_body)


def main():
    if len(sys.argv) != 2:
        print('usage: python3 obelix.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]

    io = RobotIO(config_arg)
    io.setup()
    mission = Mission(io, relative=True, rosbag=True)

    mission.start_logs()

    mission.spin()
    mission.start(z_start=0.3, ramp_duration=5, prompt=True)

    mission.goto(
        0, 0, 0.5, 2, 
        duration=0, prompt=True)
    mission.goto(
        0, 0, 0.5, -2,
        duration=0, prompt=True)
    mission.gotoz(z=0.1, prompt=True)

    mission.stop(prompt=True)


if __name__ == '__main__':
    raise SystemExit(main())
