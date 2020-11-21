"""Testing ``manim -`` command.
"""

import subprocess
import sys


def test_manim_terminal_input_python(tmpdir):
    test_scene = """
from manim import *
class Some(Scene):
    def construct(self):
        self.play(Write(Text("Hello")))
    """
    process = subprocess.Popen(
        [sys.executable, "-m", "manim", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        cwd=tmpdir,
    )
    stdout_data = process.communicate(input=test_scene.encode())[0]
    print(stdout_data.decode())
    assert (tmpdir / "media" / "videos" / "-" / "1080p60" / "Some.mp4").exists()


def test_manim_terminal_input_manim(tmpdir):
    test_scene = """
from manim import *
class Some(Scene):
    def construct(self):
        self.play(Write(Text("Hello")))
    """
    # TODO: Find the manim executable automatically seaching in site-packages directory
    # so user can actually run pytest without any issue.
    process = subprocess.Popen(
        ["manim", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        cwd=tmpdir,
    )
    stdout_data = process.communicate(input=test_scene.encode())[0]
    print(stdout_data.decode())
    assert (tmpdir / "media" / "videos" / "-" / "1080p60" / "Some.mp4").exists()
