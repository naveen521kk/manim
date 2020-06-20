from manim.logger import logger
from manim.config import parse_cli
from gooey import Gooey, GooeyParser

__all__ = ["gooey_cli"]

def gooey_cli():
    logger.info("Starting GUI")
    parser = GooeyParser()
    parser.add_argument(
            "file",
            help="Path to file holding the python code for the scene",
            widget="FileChooser"
    )
    parser.add_argument(
            "--media_dir",
            help="Directory to write media",
            widget="DirChooser"
    )
    video_group = parser.add_mutually_exclusive_group()
    video_group.add_argument(
            "--video_dir",
            help="Directory to write file tree for video",
            widget="DirChooser"
    )
    parser.add_argument(
            "--tex_dir",
            help="Directory to write tex",
            widget="DirChooser"
    )
    parser.add_argument(
            "--text_dir",
            help="Directory to write text",
            widget="DirChooser"
    )
    parser.add_argument(
            "--tex_template",
            help="Specify a custom TeX template file",
            widget="FileChooser"
    )
    return parse_cli(parser=parser)