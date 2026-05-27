from genomstack import RobotIO, Mission
from genomstack.utils import quat2euler, quat2yaw
import time


io = RobotIO('tilthex_simu')
mission = Mission(io)

io.setup()

p_dict = io.read('pom_mocap', 'frame/robot')
print(p_dict['pos'])


time.sleep(3)
mission.start_logs()

mission.spin()
mission.start(z_start=0.05, prompt=True)

mission.take_off(0.15, prompt=True)

mission.goto(-2, 0, 0.5, 1.5, prompt=True)

mission.land(z=0.2, prompt=True)
mission.stop(prompt=True)
