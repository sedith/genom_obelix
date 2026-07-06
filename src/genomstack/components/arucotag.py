from .base import Component
from genomix import GenoMError


class ArucoTag(Component):
    def setup(self) -> None:
        self.connect_port('frame', 'gazebocam/image/gray')
        self.connect_port('drone', 'pom/frame/robot')

        if 'intrinsics' in self.component_cfg:
            self.call('set_intrinsics', *self.component_cfg.intrinsics)
        self.call('set_length', 0.2)
        self.call('set_aruco_dict', 'DICT_6X6_250')
        self.call('set_cameratobody_tf', self.component_cfg.cam_to_body_tf)
        self.call('output_frame', self.component_cfg.output_frame)

        for i in self.component_cfg.markers:
            try:
                self.call('remove_marker', str(i))
            except GenoMError:
                pass
            self.call('add_marker', str(i))
