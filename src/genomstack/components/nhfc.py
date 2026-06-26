from .base import Component


class Nhfc(Component):
    START_ORDER = 40

    def setup(self) -> None:
        self.call('set_gtmrp_geom', self.cfg.geom)
        self.call('set_mass', mass=self.cfg.inertial.mass)
        self.call('set_control_mode', att_mode='::nhfc::tilt_prioritized')
        self.call('set_servo_gain', gain=self.component_cfg.gain)
        self.call('set_saturation', sat={
            'x': 1,
            'v': 1,
            'ix': 0,
        })
        self.call('set_emerg', emerg={
            'descent': 0.5,
            'dx': 0.1,
            'dq': 0.1,
            'dv': 9.5,
            'dw': 19.5,
        })

        self.connect_port('state', 'pom/frame/robot')
        self.connect_port('reference', 'maneuver/desired')

    def start(self) -> None:
        self.call('servo', ack=True)
