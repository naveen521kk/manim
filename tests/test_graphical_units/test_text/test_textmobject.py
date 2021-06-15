from ...utils.GraphicalUnitTester import GraphicalUnitTester
from ...utils.testing_utils import get_scenes_to_test
import pytest
from manim import *
from ...helpers.font_utils import fc_register_font
# def test_simple(setup_fontconfig,fonts_dir):
#     with fc_register_font(fonts_dir / "Barlow-Regular.ttf") as f:
#         a = manim.Text("Hello")
#         assert Path(a.file_path).exists()

class SimpleTextTest(Scene):  # e.g. RoundedRectangleTest
    def construct(self):
        with fc_register_font("Barlow-Regular.ttf") as font:
            text = Text("Hello World", font='Barlow-Regular')
        self.play(Write(text))

class ItalicSlantTextTest(Scene):  # e.g. RoundedRectangleTest
    def construct(self):
        with fc_register_font("Barlow-Regular.ttf") as font:
            text = Text("Hello World", font='Barlow-Regular', slant=ITALIC)
        self.play(Write(text))

@pytest.mark.slow
@pytest.mark.parametrize("scene_to_test", get_scenes_to_test(__name__), indirect=False)
def test_scene(scene_to_test, tmpdir, show_diff):
    GraphicalUnitTester(scene_to_test[1], "text_mobject", tmpdir).test(show_diff=show_diff)
