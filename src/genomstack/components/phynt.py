import math
from .base import Component


class Phynt(Component):
    START_ORDER = 30

    def setup(self) -> None:
        self.call('set_mass', self.cfg.inertial.mass)
        self.call('set_geom', self.cfg.inertial.J)

        self.call('set_wo_gains', self.component_cfg.wo.K)
        self.call('set_wo_thresh', self.component_cfg.wo.thresh)
        self.call('set_wo_fc', self.component_cfg.wo.fc)
        self.call('set_wo_bias', self.component_cfg.wo.bias)

        af = self.critical_damping()
        self.call('set_af_parameters', {
            'mass': self.cfg.inertial.mass,
            'B': self.critical_damping(),
            'K': self.component_cfg.af.K,
            'J': self.cfg.inertial.J,
         })

        self.call('enable', {'enable': {'wo': True, 'af': True}})

        self.connect_port('state', 'pom/frame/robot')
        self.connect_port('reference', 'maneuver/desired')
        self.connect_port('wrench_measure', 'nhfc/wrench_measure')

    def start(self) -> None:
        self.call('stop', ack=True)
        self.call('set_current_position')
        self.call('servo', ack=True)

    def critical_damping(self) -> dict:
        m = self.cfg.inertial.mass
        K = self.component_cfg.af.K
        return [
            2 * math.sqrt(K[0] * m),
            2 * math.sqrt(K[1] * m),
            2 * math.sqrt(K[2] * m),
            2 * math.sqrt(K[3]),
            2 * math.sqrt(K[4]),
            2 * math.sqrt(K[5]),
        ]
