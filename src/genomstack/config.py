from __future__ import annotations
from pathlib import Path
import time
import yaml


def find_workspace_root(start: Path | None = None) -> Path:
    start = (start or Path(__file__)).resolve()  # works since genomstack is installed in editable mode
    for p in [start, *start.parents]:
        if (p / 'pyproject.toml').exists():
            return p
    raise RuntimeError('Could not determine workspace root.')


class AttrDict(dict):
    """Makes dict accessible by attributes.
    Made partly after https://stackoverflow.com/a/1639632/6494418
    """
    def __init__(self, dictionary):
        for key in dictionary:
            self.__setitem__(key, dictionary[key])

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            super(AttrDict, self).__setitem__(key, AttrDict(value))
        elif isinstance(value, list):
            super(AttrDict, self).__setitem__(key, [AttrDict(v) if isinstance(v, dict) else v for v in value])
        else:
            super(AttrDict, self).__setitem__(key, value)
        super(AttrDict, self).__setattr__(key, self[key])

    def __setattr__(self, key, value):
        self.__setitem__(key, value)


class Config(AttrDict):
    def __init__(self, config_file: str | Path):
        self.root = find_workspace_root()

        self.config_file = Path(config_file)
        if self.config_file.is_absolute():
            pass
        elif self.config_file.parent == Path('.'):
            self.config_file = self.root / 'config' / self.config_file
        else:
            self.config_file = self.root / self.config_file
        if not self.config_file.suffix:
            self.config_file = self.config_file.with_suffix(".yaml")

        with open(self.config_file, 'r') as f:
            yaml_dict = yaml.safe_load(f)

        super(Config, self).__init__(yaml_dict)

        self.tmp_path = Path(self.tmp_path)
        if 'workspace' in self and self.workspace:
            self.workspace = Path(self.workspace)
        if 'plugin_path' in self and self.plugin_path:
            self.plugin_path = Path(self.plugin_path)
        if 'setup' in self and self.setup:
            self.setup = [Path(path) for path in self.setup]

        self.inertial.J = [
            self.inertial.Jxx, 0.0, 0.0, 
            0.0, self.inertial.Jyy, 0.0,
            0.0, 0.0, self.inertial.Jzz,
        ]

        if 'rotorcraft' in self.components:
            self.components.rotorcraft.calib_file = self.root / 'calib' / self.components.rotorcraft.calib
        self.log_dir = self.root / 'logs' / f'{time.strftime("%y%m%d_%H%M%S")}_{self.config_file.stem}'

        if 'ros2' not in yaml_dict or self.ros2 is None:
            self.ros2 = {'enabled': False}

        if 'external_publishers' not in yaml_dict or self.external_publishers is None:
            self.external_publishers = {}


def load_config(config_file: str | Path) -> Config:
    return Config(config_file=config_file)
