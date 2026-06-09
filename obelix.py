#!/usr/bin/env python3
import sys
import time
from genomstack import RobotIO, Mission
from genomstack.utils import quat2euler, quat2yaw


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

    mission.goto(-1, -1, 2, 0.00, prompt=True)
    mission.goto( 1, -1, 3, 1.57, prompt=True)
    mission.goto( 1,  1, 1, 3, prompt=True)
    mission.goto(-1,  1, 4, -1, prompt=True)
    mission.goto(0, 0, 2, 0, prompt=True)

    mission.land(z=0.2, prompt=True)
    mission.stop(prompt=True)


if __name__ == '__main__':
    raise SystemExit(main())
