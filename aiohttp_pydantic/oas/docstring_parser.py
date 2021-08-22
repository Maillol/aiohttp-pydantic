"""
Utility to extract extra OAS description from docstring.
"""

import re
import textwrap
from typing import Dict, List


class LinesIterator:
    def __init__(self, lines: str):
        self._lines = lines.splitlines()
        self._i = -1

    def next_line(self) -> str:
        if self._i == len(self._lines) - 1:
            raise StopIteration from None
        self._i += 1
        return self._lines[self._i]

    def rewind(self) -> str:
        if self._i == -1:
            raise StopIteration from None
        self._i -= 1
        return self._lines[self._i]

    def __iter__(self):
        return self

    def __next__(self):
        return self.next_line()


def _i_extract_block(lines: LinesIterator):
    """
    Iter the line within an indented block and dedent them.
    """

    # Go to the first not empty or not white space line.
    try:
        line = next(lines)
    except StopIteration:
        return  # No block to extract.
    while line.strip() == "":
        try:
            line = next(lines)
        except StopIteration:
            return

    indent = re.fullmatch("( *).*", line).groups()[0]
    indentation = len(indent)
    start_of_other_block = re.compile(f" {{0,{indentation}}}[^ ].*")
    yield line[indentation:]

    # Yield lines until the indentation is the same or is greater than
    # the first block line.
    try:
        line = next(lines)
    except StopIteration:
        return
    while not start_of_other_block.fullmatch(line):
        yield line[indentation:]
        try:
            line = next(lines)
        except StopIteration:
            return

    lines.rewind()


def _dedent_under_first_line(text: str) -> str:
    """
    Apply textwrap.dedent ignoring the first line.
    """
    lines = text.splitlines()
    other_lines = "\n".join(lines[1:])
    if other_lines:
        return f"{lines[0]}\n{textwrap.dedent(other_lines)}"
    return text


def status_code(docstring: str) -> Dict[int, str]:
    """
    Extract the "Status Code:" block of the docstring.
    """
    iterator = LinesIterator(docstring)
    for line in iterator:
        if re.fullmatch("status\\s+codes?\\s*:", line, re.IGNORECASE):
            iterator.rewind()
            blocks = []
            lines = []
            i_block = _i_extract_block(iterator)
            next(i_block)
            for line_of_block in i_block:
                if re.search("^\\s*\\d{3}\\s*:", line_of_block):
                    if lines:
                        blocks.append("\n".join(lines))
                        lines = []
                lines.append(line_of_block)
            if lines:
                blocks.append("\n".join(lines))

            return {
                int(status.strip()): _dedent_under_first_line(desc.strip())
                for status, desc in (block.split(":", 1) for block in blocks)
            }
    return {}


def tags(docstring: str) -> List[str]:
    """
    Extract the "Tags:" block of the docstring.
    """
    iterator = LinesIterator(docstring)
    for line in iterator:
        if re.fullmatch("tags\\s*:.*", line, re.IGNORECASE):
            iterator.rewind()
            lines = " ".join(_i_extract_block(iterator))
            return [" ".join(e.split()) for e in re.split("[,;]", lines.split(":")[1])]
    return []


def operation(docstring: str) -> str:
    """
    Extract all docstring except the "Status Code:" block.
    """
    lines = LinesIterator(docstring)
    ret = []
    for line in lines:
        if re.fullmatch("status\\s+codes?\\s*:|tags\\s*:.*", line, re.IGNORECASE):
            lines.rewind()
            for _ in _i_extract_block(lines):
                pass
        else:
            ret.append(line)
    return ("\n".join(ret)).strip()
