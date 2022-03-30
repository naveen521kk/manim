from __future__ import annotations
from manim.constants import WHITE
from manim.utils.color import Color
from dataclasses import dataclass
from copy import deepcopy
import typing

ValidColor = typing.Union[str, Color, None]

@dataclass
class TextUnderline:
    underline: bool
    underline_color: ValidColor = None

@dataclass
class TextOverline:
    overline: bool
    overline_color: ValidColor = None

@dataclass
class TextStrikethrough:
    strikethrough: bool
    strikethrough_color: ValidColor = None

@dataclass
class FormattedString:
    text: str = ""
    font: str | None = None
    fallback_font: str | None = None
    font_size: int = None
    color: str | Color = WHITE
    strikethrough: TextStrikethrough = None
    insert_hypens: bool = True
    underline: TextUnderline = None
    overline: TextOverline = None

    def clear(self):
        self.text = ""

    def __add__(self, a: FormattedString, b: FormattedString | str):
        _new_obj = deepcopy(a)
        if isinstance(b, FormattedString):
            _new_obj.text += b.text
        else:
            _new_obj.text += b
        return _new_obj
