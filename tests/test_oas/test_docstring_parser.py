from textwrap import dedent

from aiohttp_pydantic.oas.docstring_parser import (
    status_code,
    tags,
    operation,
    _i_extract_block,
    LinesIterator,
)
from inspect import getdoc
import pytest


def web_handler():
    """
    bla bla bla


    Tags: tag1,  tag2
      , tag3,

      t   a
      g
         4

    Status Codes:
        200: line 1

          line 2:
            - line 3
            - line 4

          line 5

        300: line A 1

        301: line B 1
          line B 2
        400: line C 1

             line C 2

               line C 3

    bla bla
    """


def web_handler_2():
    """
    bla bla bla


    Tags: tag1
    Status Codes:
        200: line 1

    bla bla
    """


def test_lines_iterator():
    lines_iterator = LinesIterator("AAAA\nBBBB")
    with pytest.raises(StopIteration):
        lines_iterator.rewind()

    assert lines_iterator.next_line() == "AAAA"
    assert lines_iterator.rewind()
    assert lines_iterator.next_line() == "AAAA"
    assert lines_iterator.next_line() == "BBBB"
    with pytest.raises(StopIteration):
        lines_iterator.next_line()


def test_status_code():

    expected = {
        200: "line 1\n\nline 2:\n  - line 3\n  - line 4\n\nline 5",
        300: "line A 1",
        301: "line B 1\nline B 2",
        400: "line C 1\n\nline C 2\n\n  line C 3",
    }

    assert status_code(getdoc(web_handler)) == expected


def test_tags():
    expected = ["tag1", "tag2", "tag3", "t a g 4"]
    assert tags(getdoc(web_handler)) == expected


def test_operation():
    expected = "bla bla bla\n\n\nbla bla"
    assert operation(getdoc(web_handler)) == expected
    assert operation(getdoc(web_handler_2)) == expected


def test_i_extract_block():

    blocks = dedent(
        """
    aaaa:

      bbbb
    
      cccc
    dddd
    """
    )

    lines = LinesIterator(blocks)
    text = "\n".join(_i_extract_block(lines))
    assert text == """aaaa:\n\n  bbbb\n\n  cccc"""

    blocks = dedent(
        """
    aaaa:

      bbbb

      cccc

    dddd
    """
    )

    lines = LinesIterator(blocks)
    text = "\n".join(_i_extract_block(lines))
    assert text == """aaaa:\n\n  bbbb\n\n  cccc\n"""

    blocks = dedent(
        """
    aaaa:

      bbbb

      cccc
    """
    )

    lines = LinesIterator(blocks)
    text = "\n".join(_i_extract_block(lines))
    assert text == """aaaa:\n\n  bbbb\n\n  cccc"""

    lines = LinesIterator("")
    text = "\n".join(_i_extract_block(lines))
    assert text == ""

    lines = LinesIterator("\n")
    text = "\n".join(_i_extract_block(lines))
    assert text == ""

    lines = LinesIterator("aaaa:")
    text = "\n".join(_i_extract_block(lines))
    assert text == "aaaa:"
