from dataclasses import dataclass, KW_ONLY, asdict
from enum import Enum
from manimpango import Style, Weight, Variant, FontDescription

__all__ = [
    "Style",
    "Weight",
    "Variant",
    "Underline",
    "Overline",
    "Strikethrough",
    "Font",
    "TextColor",
    "FormattedString",
]


@dataclass
class Underline:
    enable: bool = None
    color: str = None


@dataclass
class Overline:
    enable: bool = None
    color: str = None


@dataclass
class Strikethrough:
    enable: bool = None
    color: str = None


@dataclass
class Font:
    string: str = None
    _: KW_ONLY  # other parameters are keyword-only
    family: str = None
    size: int = None
    style: str | Style = None
    weight: Weight = None
    variant: Variant = None
    fallback_font: str = None

    def __post_init__(self):
        if self.string:
            fd = FontDescription.from_string(self.string)
            self.family = fd.family
            self.size = fd.size
            self.style = fd.style
            self.weight = fd.weight
            self.variant = fd.variant


@dataclass
class TextColor:
    foreground_color: str = None
    foreground_alpha: float = None
    background_color: str = None
    background_alpha: float = None


class Variant(Enum):
    NORMAL = Variant.NORMAL
    SMALL_CAPS = Variant.SMALL_CAPS


@dataclass
class FormattedString:
    text: str
    _: KW_ONLY  # other parameters are keyword-only
    font: str | Font = None
    color: str | TextColor = None
    strikethrough: bool | Strikethrough = None
    insert_hyphens: bool = None
    underline: bool | Underline = None
    overline: bool | Overline = None
    letter_spacing: float = None

    def __post_init__(self):
        if isinstance(self.font, str):
            self.font = Font(self.font)
        if isinstance(self.strikethrough, bool):
            self.strikethrough = Strikethrough(enable=self.strikethrough)
        if isinstance(self.underline, bool):
            self.underline = Underline(enable=self.underline)
        if isinstance(self.overline, bool):
            self.overline = Overline(enable=self.overline)
        if isinstance(self.color, str):
            self.color = TextColor(foreground_color=self.color)

    def __add__(self, other):
        if isinstance(other, str):
            self.text += other
        elif isinstance(other, FormattedString):
            raise TypeError("Concatenating two FormattedStrings is ambiguous.")
        else:
            raise TypeError(f"Cannot concatenate FormattedString and {type(other)!r}.")
        return self

    def __radd__(self, other):
        if isinstance(other, str):
            self.text = other + self.text
        elif isinstance(other, FormattedString):
            raise TypeError("Concatenating two FormattedStrings is ambiguous.")
        else:
            raise TypeError(f"Cannot concatenate FormattedString and {type(other)!r}.")
        return self

    def __str__(self) -> str:
        return self.text

    def __repr__(self):
        return f"FormattedString({self.text!r})"

    def __eq__(self, other):
        if isinstance(other, str):
            return self.text == other
        elif isinstance(other, FormattedString):
            return asdict(self) == asdict(other)
        else:
            return False

    def __len__(self):
        return len(self.text)
