from .base import Component
import json


class Rotorcraft(Component):
    def setup(self) -> None:
        self.call('connect', {
            'serial': self.component_cfg.serial,
            'baud': 0,
        })

        self.call('set_sensor_rate', {
            'rate': {'imu': 1000, 'mag': 0, 'motor': 20, 'battery': 1}
        })
        self.call('set_imu_filter', {
            'gfc': [20, 20, 20],
            'afc': [5, 5, 5],
            'mfc': [20, 20, 20],
        })

        if self.component_cfg.calib:
            calib = json.load(open(self.component_cfg.calib_file))
            calib['imu_calibration']['astddev'] = [
                s*10 for s in calib['imu_calibration']['astddev']
            ]
            self.call('set_imu_calibration', calib)

        self.connect_port('rotor_input', 'nhfc/rotor_input')

        self.call('stop')
