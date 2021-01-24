from ..camera.skia_camera import SkiaCamera
from .scene import Scene

class SkiaScene(Scene):
    def __init__(self,**kwargs):
        #super.__init__(camera_class=SkiaCamera,**kwargs)
        super(SkiaScene, self).__init__(camera_class=SkiaCamera,**kwargs)