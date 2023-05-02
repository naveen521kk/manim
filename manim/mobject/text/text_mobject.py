"""Mobjects used for displaying (non-LaTeX) text.

.. note::
   Just as you can use :class:`~.Tex` and :class:`~.MathTex` (from the module :mod:`~.tex_mobject`)
   to insert LaTeX to your videos, you can use :class:`~.Text` to to add normal text.

.. important::

   See the corresponding tutorial :ref:`using-text-objects`, especially for information about fonts.


The simplest way to add text to your animations is to use the :class:`~.Text` class. It uses the Pango library to render text.
With Pango, you are also able to render non-English alphabets like `你好` or  `こんにちは` or `안녕하세요` or `مرحبا بالعالم`.

Examples
--------

.. manim:: HelloWorld
    :save_last_frame:

    class HelloWorld(Scene):
        def construct(self):
            text = Text('Hello world').scale(3)
            self.add(text)

.. manim:: TextAlignment
    :save_last_frame:

    class TextAlignment(Scene):
        def construct(self):
            title = Text("K-means clustering and Logistic Regression", color=WHITE)
            title.scale(0.75)
            self.add(title.to_edge(UP))

            t1 = Text("1. Measuring").set_color(WHITE)

            t2 = Text("2. Clustering").set_color(WHITE)

            t3 = Text("3. Regression").set_color(WHITE)

            t4 = Text("4. Prediction").set_color(WHITE)

            x = VGroup(t1, t2, t3, t4).arrange(direction=DOWN, aligned_edge=LEFT).scale(0.7).next_to(ORIGIN,DR)
            x.set_opacity(0.5)
            x.submobjects[1].set_opacity(1)
            self.add(x)

"""

from __future__ import annotations

__all__ = ["Text", "Paragraph", "MarkupText", "register_font"]


import copy
import hashlib
import os
import re
from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from typing import Iterable, Sequence

import manimpango
import numpy as np
from colour import Color
from manimpango import MarkupUtils, PangoUtils, TextSetting

from manim import config, logger
from manim.constants import *
from manim.mobject.geometry.arc import Dot
from manim.mobject.svg.svg_mobject import SVGMobject
from manim.mobject.types.vectorized_mobject import VGroup, VMobject
from manim.utils.color import Colors, color_gradient
from manim.utils.deprecation import deprecated
from manim.mobject.text.formatted_string import FormattedString, Font
from manimpango import SVGRenderer, Layout, TextAttribute, FontDescription

TEXT_MOB_SCALE_FACTOR = 0.05
DEFAULT_LINE_SPACING_SCALE = 0.3
TEXT2SVG_ADJUSTMENT_FACTOR = 4.8


class Text(SVGMobject):
    r"""Display (non-LaTeX) text rendered using `Pango <https://pango.gnome.org/>`_.

    Text objects behave like a :class:`.VGroup`-like iterable of all characters
    in the given text. In particular, slicing is possible.

    **What is PangoMarkup?**

    PangoMarkup is a small markup language like html and it helps you avoid using
    "range of characters" while coloring or styling a piece a Text. You can use
    this language with :class:`~.MarkupText`.

    A simple example of a marked-up string might be::

        <span foreground="blue" size="x-large">Blue text</span> is <i>cool</i>!"

    and it can be used with :class:`~.MarkupText` as

    .. manim:: MarkupExample
        :save_last_frame:

        class MarkupExample(Scene):
            def construct(self):
                text = MarkupText('<span foreground="blue" size="x-large">Blue text</span> is <i>cool</i>!"')
                self.add(text)

    A more elaborate example would be:

    .. manim:: MarkupElaborateExample
        :save_last_frame:

        class MarkupElaborateExample(Scene):
            def construct(self):
                text = MarkupText(
                    '<span foreground="purple">ا</span><span foreground="red">َ</span>'
                    'ل<span foreground="blue">ْ</span>ع<span foreground="red">َ</span>ر'
                    '<span foreground="red">َ</span>ب<span foreground="red">ِ</span>ي'
                    '<span foreground="green">ّ</span><span foreground="red">َ</span>ة'
                    '<span foreground="blue">ُ</span>'
                )
                self.add(text)

    PangoMarkup can also contain XML features such as numeric character
    entities such as ``&#169;`` for © can be used too.

    The most general markup tag is ``<span>``, then there are some
    convenience tags.

    Here is a list of supported tags:

    - ``<b>bold</b>``, ``<i>italic</i>`` and ``<b><i>bold+italic</i></b>``
    - ``<ul>underline</ul>`` and ``<s>strike through</s>``
    - ``<tt>typewriter font</tt>``
    - ``<big>bigger font</big>`` and ``<small>smaller font</small>``
    - ``<sup>superscript</sup>`` and ``<sub>subscript</sub>``
    - ``<span underline="double" underline_color="green">double underline</span>``
    - ``<span underline="error">error underline</span>``
    - ``<span overline="single" overline_color="green">overline</span>``
    - ``<span strikethrough="true" strikethrough_color="red">strikethrough</span>``
    - ``<span font_family="sans">temporary change of font</span>``
    - ``<span foreground="red">temporary change of color</span>``
    - ``<span fgcolor="red">temporary change of color</span>``
    - ``<gradient from="YELLOW" to="RED">temporary gradient</gradient>``

    For ``<span>`` markup, colors can be specified either as
    hex triples like ``#aabbcc`` or as named CSS colors like
    ``AliceBlue``.
    The ``<gradient>`` tag is handled by Manim rather than
    Pango, and supports hex triplets or Manim constants like
    ``RED`` or ``RED_A``.
    If you want to use Manim constants like ``RED_A`` together
    with ``<span>``, you will need to use Python's f-String
    syntax as follows::

        MarkupText(f'<span foreground="{RED_A}">here you go</span>')

    If your text contains ligatures, the :class:`MarkupText` class may
    incorrectly determine the first and last letter when creating the
    gradient. This is due to the fact that ``fl`` are two separate characters,
    but might be set as one single glyph - a ligature. If your language
    does not depend on ligatures, consider setting ``disable_ligatures``
    to ``True``. If you must use ligatures, the ``gradient`` tag supports an optional
    attribute ``offset`` which can be used to compensate for that error.

    For example:

    - ``<gradient from="RED" to="YELLOW" offset="1">example</gradient>`` to *start* the gradient one letter earlier
    - ``<gradient from="RED" to="YELLOW" offset=",1">example</gradient>`` to *end* the gradient one letter earlier
    - ``<gradient from="RED" to="YELLOW" offset="2,1">example</gradient>`` to *start* the gradient two letters earlier and *end* it one letter earlier

    Specifying a second offset may be necessary if the text to be colored does
    itself contain ligatures. The same can happen when using HTML entities for
    special chars.

    When using ``underline``, ``overline`` or ``strikethrough`` together with
    ``<gradient>`` tags, you will also need to use the offset, because
    underlines are additional paths in the final :class:`SVGMobject`.
    Check out the following example.

    Escaping of special characters: ``>`` **should** be written as ``&gt;``
    whereas ``<`` and ``&`` *must* be written as ``&lt;`` and
    ``&amp;``.

    You can find more information about Pango markup formatting at the
    corresponding documentation page:
    `Pango Markup <https://docs.gtk.org/Pango/pango_markup.html>`_.
    Please be aware that not all features are supported by this class and that
    the ``<gradient>`` tag mentioned above is not supported by Pango.

    Parameters
    ----------

    text
        The text that needs to be created as mobject.
    fill_opacity
        The fill opacity, with 1 meaning opaque and 0 meaning transparent.
    stroke_width
        Stroke width.
    font_size
        Font size.
    line_spacing
        Line spacing.
    font
        Global font setting for the entire text. Local overrides are possible.
    slant
        Global slant setting, e.g. `NORMAL` or `ITALIC`. Local overrides are possible.
    weight
        Global weight setting, e.g. `NORMAL` or `BOLD`. Local overrides are possible.
    gradient
        Global gradient setting. Local overrides are possible.
    warn_missing_font
        If True (default), Manim will issue a warning if the font does not exist in the
        (case-sensitive) list of fonts returned from `manimpango.list_fonts()`.

    Returns
    -------
    :class:`MarkupText`
        The text displayed in form of a :class:`.VGroup`-like mobject.

    Examples
    ---------

    .. manim:: BasicMarkupExample
        :save_last_frame:

        class BasicMarkupExample(Scene):
            def construct(self):
                text1 = MarkupText("<b>foo</b> <i>bar</i> <b><i>foobar</i></b>")
                text2 = MarkupText("<s>foo</s> <u>bar</u> <big>big</big> <small>small</small>")
                text3 = MarkupText("H<sub>2</sub>O and H<sub>3</sub>O<sup>+</sup>")
                text4 = MarkupText("type <tt>help</tt> for help")
                text5 = MarkupText(
                    '<span underline="double">foo</span> <span underline="error">bar</span>'
                )
                group = VGroup(text1, text2, text3, text4, text5).arrange(DOWN)
                self.add(group)

    .. manim:: ColorExample
        :save_last_frame:

        class ColorExample(Scene):
            def construct(self):
                text1 = MarkupText(
                    f'all in red <span fgcolor="{YELLOW}">except this</span>', color=RED
                )
                text2 = MarkupText("nice gradient", gradient=(BLUE, GREEN))
                text3 = MarkupText(
                    'nice <gradient from="RED" to="YELLOW">intermediate</gradient> gradient',
                    gradient=(BLUE, GREEN),
                )
                text4 = MarkupText(
                    'fl ligature <gradient from="RED" to="YELLOW">causing trouble</gradient> here'
                )
                text5 = MarkupText(
                    'fl ligature <gradient from="RED" to="YELLOW" offset="1">defeated</gradient> with offset'
                )
                text6 = MarkupText(
                    'fl ligature <gradient from="RED" to="YELLOW" offset="1">floating</gradient> inside'
                )
                text7 = MarkupText(
                    'fl ligature <gradient from="RED" to="YELLOW" offset="1,1">floating</gradient> inside'
                )
                group = VGroup(text1, text2, text3, text4, text5, text6, text7).arrange(DOWN)
                self.add(group)

    .. manim:: UnderlineExample
        :save_last_frame:

        class UnderlineExample(Scene):
            def construct(self):
                text1 = MarkupText(
                    '<span underline="double" underline_color="green">bla</span>'
                )
                text2 = MarkupText(
                    '<span underline="single" underline_color="green">xxx</span><gradient from="#ffff00" to="RED">aabb</gradient>y'
                )
                text3 = MarkupText(
                    '<span underline="single" underline_color="green">xxx</span><gradient from="#ffff00" to="RED" offset="-1">aabb</gradient>y'
                )
                text4 = MarkupText(
                    '<span underline="double" underline_color="green">xxx</span><gradient from="#ffff00" to="RED">aabb</gradient>y'
                )
                text5 = MarkupText(
                    '<span underline="double" underline_color="green">xxx</span><gradient from="#ffff00" to="RED" offset="-2">aabb</gradient>y'
                )
                group = VGroup(text1, text2, text3, text4, text5).arrange(DOWN)
                self.add(group)

    .. manim:: FontExample
        :save_last_frame:

        class FontExample(Scene):
            def construct(self):
                text1 = MarkupText(
                    'all in sans <span font_family="serif">except this</span>', font="sans"
                )
                text2 = MarkupText(
                    '<span font_family="serif">mixing</span> <span font_family="sans">fonts</span> <span font_family="monospace">is ugly</span>'
                )
                text3 = MarkupText("special char > or &gt;")
                text4 = MarkupText("special char &lt; and &amp;")
                group = VGroup(text1, text2, text3, text4).arrange(DOWN)
                self.add(group)

    .. manim:: NewlineExample
        :save_last_frame:

        class NewlineExample(Scene):
            def construct(self):
                text = MarkupText('foooo<span foreground="red">oo\nbaa</span>aar')
                self.add(text)

    .. manim:: NoLigaturesExample
        :save_last_frame:

        class NoLigaturesExample(Scene):
            def construct(self):
                text1 = MarkupText('fl<gradient from="RED" to="GREEN">oat</gradient>ing')
                text2 = MarkupText('fl<gradient from="RED" to="GREEN">oat</gradient>ing', disable_ligatures=True)
                group = VGroup(text1, text2).arrange(DOWN)
                self.add(group)


    As :class:`MarkupText` uses Pango to render text, rendering non-English
    characters is easily possible:

    .. manim:: MultiLanguage
        :save_last_frame:

        class MultiLanguage(Scene):
            def construct(self):
                morning = MarkupText("வணக்கம்", font="sans-serif")
                japanese = MarkupText(
                    '<span fgcolor="blue">日本</span>へようこそ'
                )  # works as in ``Text``.
                mess = MarkupText("Multi-Language", weight=BOLD)
                russ = MarkupText("Здравствуйте मस नम म ", font="sans-serif")
                hin = MarkupText("नमस्ते", font="sans-serif")
                chinese = MarkupText("臂猿「黛比」帶著孩子", font="sans-serif")
                group = VGroup(morning, japanese, mess, russ, hin, chinese).arrange(DOWN)
                self.add(group)

    You can justify the text by passing :attr:`justify` parameter.

    .. manim:: JustifyText

        class JustifyText(Scene):
            def construct(self):
                ipsum_text = (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                    "Praesent feugiat metus sit amet iaculis pulvinar. Nulla posuere "
                    "quam a ex aliquam, eleifend consectetur tellus viverra. Aliquam "
                    "fermentum interdum justo, nec rutrum elit pretium ac. Nam quis "
                    "leo pulvinar, dignissim est at, venenatis nisi."
                )
                justified_text = MarkupText(ipsum_text, justify=True).scale(0.4)
                not_justified_text = MarkupText(ipsum_text, justify=False).scale(0.4)
                just_title = Title("Justified")
                njust_title = Title("Not Justified")
                self.add(njust_title, not_justified_text)
                self.play(
                    FadeOut(not_justified_text),
                    FadeIn(justified_text),
                    FadeOut(njust_title),
                    FadeIn(just_title),
                )
                self.wait(1)

    Tests
    -----

    Check that the creation of :class:`~.MarkupText` works::

        >>> MarkupText('The horse does not eat cucumber salad.')
        MarkupText('The horse does not eat cucumber salad.')

    """

    def __init__(
        self,
        text: str | FormattedString | list[FormattedString] | list[str],
        font: Font | str | None = "",
        color: Color | None = None,
        gradient: tuple = None,
        line_spacing: int | None = None,
        justify: bool = False,
        height: int | None = None,
        width: int | None = None,
        should_center: bool = True,
        disable_ligatures: bool = False,
        # mobject's overriding defaults
        fill_opacity: float = 1,
        stroke_width: float = 0,
        **kwargs,
    ) -> None:
        if isinstance(font, str):
            font = Font(font)
        self.font = font
        self.line_spacing = line_spacing
        self.gradient = gradient
        self.justify = justify
        self.disable_ligatures = disable_ligatures

        self.text = None
        if isinstance(text, str):
            self.text = [FormattedString(text)]
        elif isinstance(text, FormattedString):
            self.text = [text]
        elif isinstance(text, list):
            if isinstance(text[0], str):
                self.text = [FormattedString(t) for t in text]
            elif isinstance(text[0], FormattedString):
                self.text = text
        if self.text is None:
            raise TypeError(
                "Text must be of type str or FormattedString or a list of those, "
                f"not {type(text)!r}"
            )

        self.text_color = Color(color) if color else VMobject().color
        self.text_width = width
        self.text_height = height
        file_name = self._render_svg()

        super().__init__(
            file_name,
            fill_opacity=fill_opacity,
            stroke_width=stroke_width,
            # height=config.pixel_height / config.frame_height,
            # width=config.pixel_width / config.frame_width,
            # should_center=should_center,
            **kwargs,
        )

        if self.gradient:
            self.set_color_by_gradient(*self.gradient)

    def _text2hash(self):
        """Generates ``sha256`` hash for file name."""
        # todo
        settings = "MARKUPPANGO"  # to differentiate from classical Pango Text
        settings += repr(self.line_spacing)
        settings += repr(self.disable_ligatures)
        settings += repr(self.justify)
        settings += repr(self.gradient)
        settings += repr(self.text_color)
        settings += repr(self.font)

        id_str = repr(self.text) + settings
        hasher = hashlib.sha256()
        hasher.update(id_str.encode())
        return hasher.hexdigest()[:16]

    def _get_text_for_render(self) -> str:
        return "".join((str(i) for i in self.text))

    def _get_text_attributes(self) -> list[TextAttribute]:
        texts = self.text
        text_len = 0
        text_attributes = []
        for text in texts:
            _params = {}
            
            if text.color:
                _params['foreground_color'] = text.color.foreground_color
                _params['foreground_alpha'] = text.color.foreground_alpha
                _params['background_color'] = text.color.background_color
                _params['background_alpha'] = text.color.background_alpha
            if text.font:
                _params['family'] = text.font.family
                # _params['size'] = text.font.size
                _params['fallback'] = text.font.fallback_font
                _params['weight'] = text.font.weight
                # _params['style'] = text.font.style
                # _params['variant'] = text.font.variant
            attr = TextAttribute(text_len, text_len + len(text), **_params)
            text_attributes.append(attr)
            text_len += len(text)
        return text_attributes

    def _render_svg(
        self,
    ):
        """Convert the text to SVG using Pango."""
        # check whether the text directory exists
        dir_name = config.get_dir("text_dir")
        if not dir_name.exists():
            dir_name.mkdir(parents=True)
        hash_name = self._text2hash()
        file_name = dir_name / (hash_name + ".svg")

        if file_name.exists() and False:
            svg_file = str(file_name.resolve())
        else:
            text = self._get_text_for_render()
            text_attributes = self._get_text_attributes()
            text_attributes = [
                TextAttribute(0, len(text), foreground_color=self.text_color.get_hex()),
            ] + text_attributes
            font_desc = None
            if self.font:
                font_desc = FontDescription(
                    family=self.font.family,
                    size=self.font.size,
                    style=self.font.style,
                    weight=self.font.weight,
                    variant=self.font.variant,
                )
            width=(
                    self.text_width
                    if self.text_width is not None
                    else int(config.pixel_width)
                )
            height=(
                    self.text_height
                    if self.text_height is not None
                    else int(config.pixel_height)
                )
            width=100
            height=100
            layout = Layout(
                markup=text,
                font_desc=font_desc,
                attributes=text_attributes,
                width=width,
                height=height,
            )

            renderer = SVGRenderer(
                10,
                height,
                layout,
                os.fspath(file_name.resolve())
            )
            renderer.render()
            renderer.save()
            svg_file = os.fspath(file_name.resolve())
        print(svg_file)
        return svg_file

    def __repr__(self):
        return f"MarkupText({self.text!r})"


@contextmanager
def register_font(font_file: str | Path):
    """Temporarily add a font file to Pango's search path.

    This searches for the font_file at various places. The order it searches it described below.

    1. Absolute path.
    2. In ``assets/fonts`` folder.
    3. In ``font/`` folder.
    4. In the same directory.

    Parameters
    ----------
    font_file
        The font file to add.

    Examples
    --------
    Use ``with register_font(...)`` to add a font file to search
    path.

    .. code-block:: python

        with register_font("path/to/font_file.ttf"):
            a = Text("Hello", font="Custom Font Name")

    Raises
    ------
    FileNotFoundError:
        If the font doesn't exists.

    AttributeError:
        If this method is used on macOS.

    .. important ::

        This method is available for macOS for ``ManimPango>=v0.2.3``. Using this
        method with previous releases will raise an :class:`AttributeError` on macOS.
    """

    input_folder = Path(config.input_file).parent.resolve()
    possible_paths = [
        Path(font_file),
        input_folder / "assets/fonts" / font_file,
        input_folder / "fonts" / font_file,
        input_folder / font_file,
    ]
    for path in possible_paths:
        path = path.resolve()
        if path.exists():
            file_path = path
            logger.debug("Found file at %s", file_path.absolute())
            break
    else:
        error = f"Can't find {font_file}." f"Tried these : {possible_paths}"
        raise FileNotFoundError(error)

    try:
        assert manimpango.register_font(str(file_path))
        yield
    finally:
        manimpango.unregister_font(str(file_path))


# for now paragraph is an alias for text
# in future make it so that the default width
# is the width of the screen and text wraps
# the default behaviour of Text is to not wrap
Paragraph = Text

MarkupText = Text
