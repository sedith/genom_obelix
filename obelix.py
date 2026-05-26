from genomstack import RobotIO, Mission
from genomstack.utils import quat2euler, quat2yaw
import time


# p_dict = io.read('pom_lidar', 'frame/robot')
# q_dict = 


io = RobotIO('tilthex_simu')
mission = Mission(io)

io.setup()

time.sleep(3)
mission.start_logs()

mission.spin()
mission.start(z_start=0.05, prompt=True)

mission.take_off(0.15, prompt=True)

mission.goto(5, 0, 1, 1.5, prompt=True)
mission.goto(5, 5, 2, 3, prompt=True)
mission.goto(-5, 5, 3, 1.5, prompt=True)
mission.goto(-5, -5, 2, 0, prompt=True)
mission.goto(5, -5, 1, -1.5, prompt=True)
mission.goto(5, 0, 2, -3, prompt=True)
mission.goto(0, 0, 1, 0, prompt=True)

mission.land(z=-0.5, prompt=True)
mission.stop(prompt=True)
