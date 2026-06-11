#!/usr/bin/env python3
import sys
import time
import numpy as np
from genomstack import RobotIO, Mission
from genomstack.utils import quat2euler, quat2yaw


p_ee_b = np.array([0.433, 0.25, 0.0])
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
        print('usage: python3 launch_ros2.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]

    io = RobotIO(config_arg)
    io.setup()

    mission = Mission(io, relative=True)
    mission.start_logs()

    mission.spin()
    mission.start(z_start=0.15, prompt=True)

    mission.take_off(1, prompt=True)

    mission.goto(*ee_to_body(3,3,2,np.pi), prompt=True)

    mission.goto(0, 0, 1, 0, prompt=True)
    mission.land(z=0.2, prompt=True)
    mission.stop(prompt=True)


if __name__ == '__main__':
    raise SystemExit(main())
