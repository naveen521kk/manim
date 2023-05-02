from manim.mobject.text.formatted_string import FormattedString, Font
import pytest

def test_formatted_string_init():
    a = FormattedString("abc", font="Arial")
    assert a.text == "abc"
    assert len(a) == 3
    assert a.font == Font("Arial")

def test_formatted_string_add():
    a = FormattedString("abc", font="Arial")
    assert a.text == "abc"
    assert len(a) == 3
    a += "def"
    assert a.text == "abcdef"
    assert len(a) == 6
    assert a.font == Font("Arial")

    with pytest.raises(TypeError):
        a += FormattedString("ghi", font="Arial")
        a += 1
    
    a = 'abc' + a
    assert a.text == "abcabcdef"
    assert len(a) == 9

def test_formatted_string_repr():
    a = FormattedString("abc", font="Arial")
    assert repr(a) == "FormattedString('abc')"

def test_formatted_string_eq():
    a = FormattedString("abc", font="Arial")
    b = FormattedString("abc", font="Arial")
    c = FormattedString("abc", font="Arial", color="red")
    d = FormattedString("def", font="Arial")
    assert a == b
    assert a != c
    assert a != d
    assert a == "abc"
    assert a != 1
