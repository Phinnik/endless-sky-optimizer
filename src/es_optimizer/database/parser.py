from __future__ import annotations
from dataclasses import dataclass, field
import re


@dataclass
class Node:
    level: int
    key: str | None = None
    value: str | list[str] | None = None
    children: list[Node] = field(default_factory=list)


def _is_comment_or_empty(line: str):
    return not line.lstrip() or line.startswith("#")


_TOKENIZE_PATTERN = re.compile(r"\"([^\"]*)\"|(\S+)")


def _tokenize(line: str) -> list[str]:
    match_iter = re.finditer(_TOKENIZE_PATTERN, line.replace("\t", ""))
    tokens = [m.group(1) if m.group(1) is not None else m.group(2) for m in match_iter]
    if not tokens:
        raise RuntimeError(f"Could not parse tokens for line: {line}")
    return tokens


def _get_indent(line: str) -> int:
    return len(line) - len(line.lstrip("\t"))


def make_tree(text: str) -> Node:
    lines = text.split("\n")

    root = Node(level=-1, key="__root__")
    nesting_stack = [root]

    for line in lines:
        if _is_comment_or_empty(line):
            continue

        tokens = _tokenize(line)
        indent = _get_indent(line)

        value = (
            tokens[1] if len(tokens) == 2 else (tokens[1:] if len(tokens) > 2 else None)
        )
        curr = Node(level=indent, key=tokens[0], value=value)

        while nesting_stack[-1].level >= indent:
            nesting_stack.pop()

        nesting_stack[-1].children.append(curr)
        nesting_stack.append(curr)
    return root
