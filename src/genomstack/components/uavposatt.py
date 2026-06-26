from .base import Component


class UavPos(Component):
    START_ORDER = 40

    def setup(self) -> None:
        self.call('set_mass', mass=self.cfg.inertial.mass)
        self.call('set_xyradius', rxy=self.component_cfg.xyradius)
        self.call('set_servo_gain', gain=self.component_cfg.gain)
        self.call('set_saturation', sat={
            'x': 0.3,
            'v': 0.2,
            'ix': 0,
        })

        self.connect_port('state', 'pom/frame/robot')
        self.connect_port('reference', 'maneuver/desired')

    def start(self) -> None:
        self.call('servo', ack=True)


class UavAtt(Component):
    START_ORDER = 40

    def setup(self) -> None:
        self.call('set_gtmrp_geom', self.cfg.geom)
        self.call('set_mass', mass=self.cfg.inertial.mass)
        self.call('set_servo_gain', gain=self.component_cfg.gain)
        self.call('set_emerg', emerg={
            'dq': 9.5,
            'dw': 19.5,
        })
        self.call('set_wlimit', {
            'wmin': 16,
            'wmax': 110,
        })

        self.connect_port('state', 'pom/frame/robot')
        self.connect_port('uav_input', 'uavpos/uav_input')
        self.connect_port('rotor_measure', 'rotorcraft/rotor_measure')

    def start(self) -> None:
        self.call('servo', ack=True)
