import numpy as np
from .base import Component


class GazeboCam(Component):
    def setup(self) -> None:
        for stream, topic in self.component_cfg.streams.items():
            self.call('stream', topic, stream)
            self.call('publish', stream, stream)

    def read(self, stream):
        pixmap = self.call('image', stream)['image']['images'][0]['pixmap']
        if pixmap['pixfmt'] == '::or::sensor::pixmap::MONO8':
            img = np.frombuffer(bytes(pixmap['data']), dtype=np.uint8).reshape((pixmap['height'], pixmap['width'], 1))
            img = np.clip(img, 0, 255)
        elif pixmap['pixfmt'] == '::or::sensor::pixmap::RGB8':
            img = np.frombuffer(bytes(pixmap['data']), dtype=np.uint8).reshape((pixmap['height'], pixmap['width'], 3))
            img = np.clip(img, 0, 255)
        elif pixmap['pixfmt'] == '::or::sensor::pixmap::Z32':
            img = np.frombuffer(bytes(pixmap['data']), dtype=np.float32).reshape((pixmap['height'], pixmap['width'], 1))
            img = np.clip(img, 0, 50)
        return img
