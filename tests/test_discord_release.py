"""The Discord announcement of a published release (``packaging/discord_release.py``)."""

from __future__ import annotations

import json
from pathlib import Path

import discord_release
import pytest

NOTES = Path(__file__).parent.parent / "docs" / "releases" / "1.2.2.md"
EMBED_LIMIT = 6000  # Discord counts the title, description, field and footer text of an embed
DESCRIPTION_LIMIT = 4096
TITLE_LIMIT = 256


def _release(**changes: object) -> dict[str, object]:
    release: dict[str, object] = {
        "tag_name": "v1.2.1",
        "name": "Random New World 1.2.1",
        "html_url": "https://github.com/Sir-Starch/eu5-random-new-world/releases/tag/v1.2.1",
        "published_at": "2026-11-10T02:00:40Z",
        "draft": False,
        "prerelease": False,
        "body": (
            "# Random New World 1.2.1\n\nA hotfix.\n\nIt targets **EU5 1.4.7**.\n\n"
            "## 1. Details\n\nMore."
        ),
    }
    return release | changes


def test_a_release_pings_the_role_and_only_that_role() -> None:
    payload = discord_release.build_payload(_release())
    assert payload["content"].startswith(f"<@&{discord_release.PING_ROLE}> ")
    assert payload["allowed_mentions"] == {"parse": [], "roles": [discord_release.PING_ROLE]}


def test_no_ping_leaves_the_role_out_of_text_and_permissions() -> None:
    payload = discord_release.build_payload(_release(), ping=False)
    assert "<@&" not in payload["content"]
    assert payload["allowed_mentions"] == {"parse": [], "roles": []}


def test_a_prerelease_never_pings() -> None:
    payload = discord_release.build_payload(_release(prerelease=True))
    assert "<@&" not in payload["content"]
    assert "pre-release" in payload["content"]
    assert payload["allowed_mentions"]["roles"] == []


def test_a_draft_is_not_announced() -> None:
    with pytest.raises(ValueError, match="draft"):
        _ = discord_release.build_payload(_release(draft=True))


@pytest.mark.parametrize("missing", ["tag_name", "html_url"])
def test_a_release_without_a_tag_or_link_is_refused(missing: str) -> None:
    with pytest.raises(ValueError, match="tag_name or html_url"):
        _ = discord_release.build_payload(_release(**{missing: ""}))


def test_the_embed_names_the_release_and_links_where_to_get_it() -> None:
    embed = discord_release.build_payload(_release())["embeds"][0]
    assert embed["title"] == "Random New World 1.2.1"
    assert embed["url"].endswith("/releases/tag/v1.2.1")
    assert embed.get("timestamp") == "2026-11-10T02:00:40Z"
    links = embed["fields"][0]["value"]
    assert discord_release.WORKSHOP in links
    assert embed["url"] in links
    assert discord_release.GUIDE in links


def test_a_release_without_a_name_falls_back_to_its_tag() -> None:
    assert discord_release.build_payload(_release(name=""))["embeds"][0]["title"] == "v1.2.1"


def test_the_summary_is_the_opening_before_the_first_section() -> None:
    body = _release()["body"]
    assert isinstance(body, str)
    assert discord_release.summary(body) == "A hotfix.\n\nIt targets **EU5 1.4.7**."


def test_hard_wrapped_paragraphs_are_joined_but_lists_are_not() -> None:
    notes = "A hotfix that is\nwrapped by hand.\n\nIt fixes:\n- one thing\n- another"
    assert discord_release.summary(notes) == (
        "A hotfix that is wrapped by hand.\n\nIt fixes:\n- one thing\n- another"
    )


def test_a_long_opening_is_cut_at_a_paragraph() -> None:
    paragraphs = [f"Paragraph {number} " + "x" * 250 for number in range(8)]
    text = discord_release.summary("\n\n".join(paragraphs))
    assert text.endswith(discord_release.ELLIPSIS)
    assert len(text) <= discord_release.SUMMARY_CHARS + 2
    assert text.removesuffix(f" {discord_release.ELLIPSIS}") in "\n\n".join(paragraphs)


def test_notes_that_open_with_a_section_still_give_a_summary() -> None:
    assert discord_release.summary("## What changed\n\nEverything.") == (
        "## What changed\n\nEverything."
    )


def test_the_message_fits_discords_limits_even_for_huge_notes() -> None:
    release = _release(name="N" * 400, body="word " * 20000)
    embed = discord_release.build_payload(release)["embeds"][0]
    assert len(embed["title"]) <= TITLE_LIMIT
    assert len(embed.get("description", "")) <= DESCRIPTION_LIMIT
    total = len(embed["title"]) + len(embed.get("description", "")) + len(embed["footer"]["text"])
    total += sum(len(f["name"]) + len(f["value"]) for f in embed["fields"])
    assert total < EMBED_LIMIT


def test_the_real_release_notes_make_a_clean_summary() -> None:
    text = discord_release.summary(NOTES.read_text(encoding="utf-8"))
    assert text
    assert not any(line.startswith("#") for line in text.splitlines())


def test_an_event_payload_and_a_bare_release_load_alike(tmp_path: Path) -> None:
    release = _release()
    bare, event = tmp_path / "bare.json", tmp_path / "event.json"
    _ = bare.write_text(json.dumps(release), encoding="utf-8")
    _ = event.write_text(json.dumps({"action": "published", "release": release}), encoding="utf-8")
    assert discord_release.load_release(bare) == release
    assert discord_release.load_release(event) == release


def test_only_a_discord_webhook_is_ever_posted_to() -> None:
    payload = discord_release.build_payload(_release())
    with pytest.raises(ValueError, match="webhook must be"):
        discord_release.post("https://example.invalid/api/webhooks/1/secret", payload)


def test_a_dry_run_prints_the_message_and_needs_no_webhook(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    release = tmp_path / "release.json"
    _ = release.write_text(json.dumps(_release()), encoding="utf-8")
    assert discord_release.main([str(release), "--dry-run"]) == 0
    assert '"title": "Random New World 1.2.1"' in capsys.readouterr().out


def test_a_real_run_without_a_webhook_fails_loudly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    release = tmp_path / "release.json"
    _ = release.write_text(json.dumps(_release()), encoding="utf-8")
    assert discord_release.main([str(release)]) == 1
    assert "DISCORD_WEBHOOK_URL is not set" in capsys.readouterr().err
