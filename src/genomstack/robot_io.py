from .config import Config
from .genomix import Genomix
from .components import *
from .external_publisher import ExternalPublisher


class RobotIO:
    COMPONENT_CLASSES = {
        'rotorcraft': Rotorcraft,
        'optitrack': Optitrack,
        'qualisys': Qualisys,
        'pom': Pom,
        'uavpos': UavPos,
        'uavatt': UavAtt,
        'maneuver': Maneuver,
    }

    def __init__(self, cfg: str):
        self.cfg = Config(cfg)
        self.genonix = Genomix(self.cfg)

        self.components = {}
        self.publishers = {}

        for name, component_cfg in self.cfg.components.items():
            component_type = getattr(component_cfg, 'type', name)
            component_cls = self.COMPONENT_CLASSES[component_type]
            component = component_cls(self.cfg, name)
            self.components[name] = component

        print(f'init genomix...')
        self.genonix.connect()

        for c in self.components.values():
            print(f'loading {c.name}...')
            self.genonix.load(c)

        for name, extpub_cfg in self.cfg.external_publishers.items():
            print(f'init external pub {name}...')
            extpub = ExternalPublisher(self.cfg, name, io=self)
            self.publishers[name] = extpub
        print('IO init done')

    def setup(self) -> None:
        for c in self.components.values():
            print(f'setup {c.name}...')
            c.setup()

    def read(self, component_name: str, port: str) -> dict:
        port, *subport = port.split('/')
        return self.components[component_name].call(port, *subport)

    def publish(self, publisher_name: str, msg: dict) -> None:
        self.publishers[publisher_name].publish(msg)
