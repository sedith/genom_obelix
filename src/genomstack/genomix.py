from .config import Config
from .components import Component
from .process import host_path
import genomix


class Genomix:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.g = None
        self._handles = {}

    def connect(self) -> None:
        self.g = genomix.connect(self.cfg.host)
        self.g.rpath(host_path(self.cfg.plugin_path, self.cfg.host))

    def load(self, component: Component) -> None:
        if component.name not in self._handles:
            if component.use_instance():
                self._handles[component.name] = self.g.load(component.gtype, '-i', component.name)
            else:
                self._handles[component.name] = self.g.load(component.gtype)

            component.handle = self._handles[component.name]
