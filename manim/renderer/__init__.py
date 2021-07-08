from __future__ import annotations

import typing
from abc import ABC, abstractmethod

if typing.TYPE_CHECKING:
    import numpy as np

    from ..mobject.mobject import Mobject
    from ..scene.scene import Scene
    from PIL import Image


class Renderer(ABC):
    @abstractmethod
    def init_scene(self, scene: "Scene") -> None:
        ...

    @abstractmethod
    def play(self, scene: Scene, *args, **kwargs) -> None:
        ...

    @abstractmethod
    def update_frame(
        self,
        scene: Scene,
        mobjects: typing.List[Mobject] = None,
        include_submobjects: bool = True,
        ignore_skipping: bool = True,
        **kwargs,
    ) -> None:
        ...

    @abstractmethod
    def render(
        self, scene: Scene, time: int, moving_mobjects: typing.List[Mobject]
    ) -> None:
        ...

    @abstractmethod
    def get_frame(self) -> np.ndarray:
        ...

    @abstractmethod
    def add_frame(self, frame, num_frames=1) -> None:
        ...

    @abstractmethod
    def freeze_current_frame(self, duration: float) -> None:
        ...

    @abstractmethod
    def show_frame(self) -> None:
        ...

    @abstractmethod
    def save_static_frame_data(
        self, scene: "Scene", static_mobjects: typing.Iterable[Mobject]
    ) -> np.ndarray:
        ...

    @abstractmethod
    def update_skipping_status(self):
        ...

    @abstractmethod
    def get_image(self) -> Image:
        ...

    @abstractmethod
    def scene_finished(self, scene: "Scene"):
        ...