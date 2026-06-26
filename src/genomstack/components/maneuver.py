from .base import Component
from math import pi


class Maneuver(Component):
    START_ORDER = 20

    def setup(self) -> None:
        self.call('set_bounds', {
            'xmin': -10, 'xmax': 10,
            'ymin': -10, 'ymax': 10,
            'zmin': 0, 'zmax': 10,
            'yawmin': -2*pi, 'yawmax': 2*pi,
        })

        self.call('set_velocity_limit', {
            'v': self.component_cfg.vmax,
            'w': self.component_cfg.wmax,
        })

        self.call('set_acceleration_limit', {
            'a': self.component_cfg.amax,
            'dw': self.component_cfg.dwmax,
        })

        self.connect_port('state', 'pom/frame/robot')

    def start(self) -> None:
        self.call('set_current_state')
