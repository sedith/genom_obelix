from .base import Component
from ..process import host_path


class Pom(Component):
    def setup(self) -> None:
        self.call('set_prediction_model', {
            'pmodel': '::pom::constant_acceleration'
        })
        self.call('set_process_noise', {
            'max_jerk': 100, 'max_dw': 50
        })
        self.call('set_history_length', {
            'history_length': 0.25
        })

        for meas in self.component_cfg.meas:
            self.connect_port(f'measure/{meas.name}', meas.port)
            self.call('add_measurement', meas.name, *meas.offset if 'offset' in meas else [])

    def start_log(self) -> None:
        log_dir = host_path(self.cfg.tmp_path, self.cfg.host)
        self.call('log_state', f'{log_dir}/{self.name}.log')
        self.call('log_measurements',  f'{log_dir}/{self.name}-measurements.log')
