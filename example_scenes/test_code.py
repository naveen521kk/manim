from manim import *
from pathlib import Path
import shutil
class SomeRandom(Scene):
    def construct(self):
        shutil.rmtree("media/texts",ignore_errors=True)
        a=Code(Path("test_code.py").absolute())
        self.add(a)
        self.wait(5)