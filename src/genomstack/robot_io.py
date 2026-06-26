import os
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from .config import Config
from .genomix import Genomix
from .components import *
from .external_publisher import ExternalPublisher


@contextmanager
def silence(enabled: bool = True):
    if not enabled:
        yield
        return

    with open(os.devnull, 'w') as fnull:
        with redirect_stdout(fnull), redirect_stderr(fnull):
            yield


class RobotIO:
    COMPONENT_CLASSES = {
        'rotorcraft': Rotorcraft,
        'optitrack': Optitrack,
        'qualisys': Qualisys,
        'pom': Pom,
        'uavpos': UavPos,
        'uavatt': UavAtt,
        'maneuver': Maneuver,
        'phynt': Phynt,
        'nhfc': Nhfc,
    }

    def __init__(self, cfg: str, silent: bool = False):
        self.silent = silent

        with silence(self.silent):
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
        if self.silent:
            print('silent IO instance cannot run setup!')
        for c in self.components.values():
            print(f'setup {c.name}...')
            c.setup()

    def start_components(self) -> None:
        indexed = enumerate(self.components.values())
        components = sorted(
            indexed,
            key=lambda item: (item[1].START_ORDER, item[0]),
        )

        for _, component in components:
            print(f'start {component.name}...')
            component.start()

    def read(self, component_name: str, port: str) -> dict:
        port, *subport = port.split('/')
        return self.components[component_name].call(port, *subport)

    def publish(self, publisher_name: str, msg: dict) -> None:
        self.publishers[publisher_name].publish(msg)
