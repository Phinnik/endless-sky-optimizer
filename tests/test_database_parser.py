import pytest

from es_optimizer.database.parser import Node, _get_indent, make_tree, _tokenize


@pytest.mark.parametrize(
    argnames=("line", "expected"),
    argvalues=(
        ("", 0),
        ("\t", 1),
        ("\t\t", 2),
        ("\tfoo", 1),
        ("\t foo", 1),
        ("\tfoo\t", 1),
    ),
    ids=(
        "empty",
        "only one tab",
        "only two tabs",
        "one tab",
        "one tab with space",
        "tab inside the line",
    ),
)
def test__get_indent(line: str, expected: int):
    assert _get_indent(line) == expected


@pytest.mark.parametrize(
    argnames=("line", "expected"),
    argvalues=(
        ("foo", ["foo"]),
        ("foo bar", ["foo", "bar"]),
        ('"foo" bar', ["foo", "bar"]),
        ('foo "bar"', ["foo", "bar"]),
        ("\tfoo bar", ["foo", "bar"]),
        ('"foo bar" bazz', ["foo bar", "bazz"]),
        ("foo .45", ["foo", ".45"]),
    ),
    ids=(
        "single token",
        "two tokens",
        "first token in doublequotes",
        "second token in doublequotes",
        "tabulated",
        "double doublequotes with multiple words",
        "numeric token",
    ),
)
def test___tokenize(line: str, expected: list[str]):
    assert _tokenize(line) == expected


DATA_TEXT = """
# Comment

# Another comment

Foo "bar" bazz

	child_a
		child_a.1 abc
		child_a.2 def ghi
	child_b  foo
		child_a.1 abc
		child_a.2 def ghi
	
	"child with" "many tokens" foo bar bazz


Bar bazz

"""


def test__make_tree():
    # fmt: off
    expected_tree = Node(-1, "__root__", children=[
        Node(0, "Foo", value=["bar", "bazz"], children=[
            Node(1, "child_a", children=[
                Node(2, "child_a.1", value="abc"),
                Node(2, "child_a.2", value=["def", "ghi"]),
            ]),
            Node(1, "child_b", value="foo", children=[
                Node(2, "child_a.1", value="abc"),
                Node(2, "child_a.2", value=["def", "ghi"]),
            ]),
            Node(1, "child with", value=["many tokens", "foo", "bar", "bazz"]),
        ]),
        Node(0, "Bar", value="bazz")
    ])
    # fmt: on

    tree = make_tree(DATA_TEXT)
    assert tree == expected_tree


if __name__ == "__main__":
    pytest.main(["-vv", __file__])
