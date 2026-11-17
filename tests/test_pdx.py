"""The native script grammar preserves records, character spans and strict errors."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pytest

from rnw import pdx
from rnw.progress import Cancelled
from tests.reference import pdx as reference

if TYPE_CHECKING:
    from collections.abc import Callable


def _tree(block: pdx.Block | reference.Block) -> object:
    return (
        block.open,
        block.close,
        [
            (
                entry.key,
                entry.op,
                _tree(entry.value)
                if isinstance(entry.value, (pdx.Block, reference.Block))
                else entry.value,
                entry.start,
                entry.end,
            )
            for entry in block.entries
        ],
    )


def _result(parse: Callable[[str], pdx.Block | reference.Block], text: str) -> object:
    try:
        return _tree(parse(text))
    except (pdx.PdxSyntaxError, reference.PdxSyntaxError) as error:
        return error.reason, error.offset, str(error)


@pytest.mark.parametrize(
    "text",
    [
        "",
        '# a comment\r\n x={ bare { nested } key <= "quoted\\" value" }',
        'é = { "中" x >= 2 { y } }',
        '\ufeffa = "emoji 🦊, newline\nnext"\r\n\tfoo ?= bar',
        'x = "escaped\\\nnewline"',
        'x = "unterminated',
        "a =",
        "a = }",
        "a = =",
        "a {",
        "} !",
        "} ?",
        "{{ }",
        "a != b x == y z < q z > t",
        "\ud800 = { x = \udfff }",
        "\u001c\u001d\u001e\u001f = x",
    ],
)
def test_native_script_records_equal_reference(text: str) -> None:
    assert _result(pdx.parse, text) == _result(reference.parse, text)


def test_script_lexical_boundaries_and_error_priority() -> None:
    characters = (
        "".join(chr(number) for number in range(256))
        + "\u0085\u00a0\u1680\u2000\u2007\u2028\u2029\u202f\u205f\u3000"
        + "中🦊\ufeff\ud800"
    )
    for character in characters:
        for pattern in ("a{0}b", "x={0}", 'x="{0}"', "}}{0}{{", 'x="\\{0}"'):
            text = pattern.format(character)
            assert _result(pdx.parse, text) == _result(reference.parse, text), repr(text)


def test_random_script_grammar_and_malformed_fragments() -> None:
    rng = random.Random(839)  # noqa: S311 - deterministic syntax fixtures, no secrets.
    words = ["name", "é", "🦊", "@var", "foo:bar", "-2.7", '"escaped\\" quote"']
    fragments = [*words, "{", "}", "=", ">=", "?=", "?", "!", '"', "#c\n"]
    for _ in range(1500):
        text = " ".join(rng.choices(fragments, k=rng.randrange(1, 60)))
        assert _result(pdx.parse, text) == _result(reference.parse, text), text

    def block(depth: int) -> str:
        return " ".join(
            rng.choice(words)
            + rng.choice([" = ", " >= "])
            + (
                "{ " + block(depth - 1) + " }"
                if depth and rng.randrange(3) == 0
                else rng.choice(words)
            )
            for _ in range(rng.randrange(1, 6))
        )

    for _ in range(100):
        text = block(5)
        assert _tree(pdx.parse(text)) == _tree(reference.parse(text))


def test_parser_keeps_independent_mutable_records() -> None:
    one, two = pdx.parse("x={ y=1 }"), pdx.parse("x={ y=1 }")
    assert one == two
    nested = one.block("x")
    assert nested is not None
    nested.entries.append(pdx.Entry("z", "=", "2", 0, 0))
    assert one != two
    assert len(two.block("x").entries) == 1  # pyright: ignore[reportOptionalMemberAccess]


def test_deep_script_keeps_reference_recursion_behavior() -> None:
    text = "{" * 150 + "x" + "}" * 150
    assert _tree(pdx.parse(text)) == _tree(reference.parse(text))
    text = "{" * 3000 + "x" + "}" * 3000
    with pytest.raises(RecursionError):
        _ = reference.parse(text)
    with pytest.raises(RecursionError):
        _ = pdx.parse(text)


def test_parser_cancels_between_native_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def cancel() -> None:
        nonlocal calls
        calls += 1
        if calls == 5:
            raise Cancelled

    monkeypatch.setattr(pdx, "checkpoint", cancel)
    with pytest.raises(Cancelled):
        _ = pdx.parse("x={y=1}\n" * 100_000)
    assert calls == 5
