from __future__ import annotations
from typing import Any


class Component:
    def __init__(self, cfg: Config, name: str):
        self.cfg = cfg
        self.name = name
        self.handle = None

    @property
    def component_cfg(self) -> Config:
        return self.cfg.components[self.name]

    @property
    def gtype(self) -> str:
        return self.component_cfg['type']

    def use_instance(self) -> bool:
        return self.name != self.gtype

    def port(self, port) -> str:
        return f'{self.name}/{port}'

    def call(self, method: str, *args, **kwargs) -> Any:
        """Call a service/method on the underlying GenoM handle."""

        if not hasattr(self.handle, method):
            raise AttributeError(
                f'Component {self.name} has no method {method}'
            )

        fn = getattr(self.handle, method)
        return fn(*args, **kwargs)

    def connect_port(self, local: str, remote: str) -> None:
        """Connect a local GenoM port to a remote port."""
        return self.call('connect_port', {'local': local, 'remote': remote})

    def setup(self) -> None:
        """Connect external resources, apply configuration and wire ports."""
        raise NotImplementedError()

    def start_log(self) -> None:
        """Start component-specific logging."""
        self.call('log', f'{self.cfg.tmp_dir}{self.name}.log')

    def stop_log(self) -> None:
        """Stop component-specific logging."""
        self.call('log_stop')
