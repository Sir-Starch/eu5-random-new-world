"""Announce a published GitHub release in the community's Discord channel.

``.github/workflows/discord-release.yml`` runs this when a release is published. It turns the
release into one Discord webhook message: a ping for the "Release Ping" role, and an embed with
the opening of the release notes and the places to get the release. Standard library only.

    python packaging/discord_release.py EVENT_OR_RELEASE.json [--dry-run] [--no-ping]

The file is either the release object of the GitHub API or an event payload that holds it under
``release``. The webhook URL comes from the environment (``DISCORD_WEBHOOK_URL``), never from the
command line, so it cannot end up in a process list or a log.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

WORKSHOP = "https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331"
GUIDE = "https://rnw.sirstarch.com/"
PING_ROLE = "1569953014909771806"  # "Release Ping": the role players pick in Discord's onboarding
AMBER = 0xE8A33D  # the Cartographer's gold
WEBHOOK_PREFIX = "https://discord.com/api/webhooks/"
USER_AGENT = "DiscordBot (https://github.com/Sir-Starch/eu5-random-new-world, 1)"
ELLIPSIS = "…"
DOT = "·"
SUMMARY_CHARS = 900  # an embed holds 4096, but a short opening reads better than a wall of notes
TITLE_CHARS = 256
TOO_MANY_REQUESTS = 429
SERVER_ERROR = 500
ATTEMPTS = 3
TIMEOUT_SECONDS = 30
MAX_WAIT_SECONDS = 30.0
DETAIL_CHARS = 500
BLOCK_LINE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|>|```)")


class _Field(TypedDict):
    name: str
    value: str


class _Footer(TypedDict):
    text: str


class Embed(TypedDict):
    title: str
    url: str
    color: int
    fields: list[_Field]
    footer: _Footer
    description: NotRequired[str]
    timestamp: NotRequired[str]


class _Mentions(TypedDict):
    parse: list[str]
    roles: list[str]


class Payload(TypedDict):
    content: str
    embeds: list[Embed]
    allowed_mentions: _Mentions


def _text(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) else ""


def _unwrap(text: str) -> str:
    """Join the hard-wrapped lines of each paragraph; Discord shows every wrap as a line break."""
    paragraphs: list[str] = []
    for paragraph in text.split("\n\n"):
        lines = paragraph.split("\n")
        keep = any(BLOCK_LINE.match(line) for line in lines)  # lists, quotes and code stay as is
        paragraphs.append(paragraph if keep else " ".join(line.strip() for line in lines))
    return "\n\n".join(paragraphs)


def summary(body: str, limit: int = SUMMARY_CHARS) -> str:
    """The opening of the release notes: what the release is, before its first section."""
    text = re.sub(r"\A#[ \t][^\n]*\n+", "", body.replace("\r\n", "\n").strip())  # the embed's title
    intro = _unwrap(re.split(r"(?m)^#{2,6}[ \t]", text, maxsplit=1)[0].strip() or text)
    if len(intro) <= limit:
        return intro
    head = intro[:limit]
    for separator, keep in (("\n\n", 0), (". ", 1)):
        cut = head.rfind(separator)
        if cut > limit // 2:
            return f"{head[: cut + keep].rstrip()} {ELLIPSIS}"
    return f"{head.rstrip()}{ELLIPSIS}"


def build_payload(release: Mapping[str, object], *, ping: bool = True) -> Payload:
    """The webhook message for a published release; a pre-release never pings."""
    if release.get("draft") is True:
        msg = "a draft is not announced"
        raise ValueError(msg)
    tag, url = _text(release, "tag_name"), _text(release, "html_url")
    if not tag or not url:
        msg = "the release has no tag_name or html_url"
        raise ValueError(msg)
    name = _text(release, "name") or tag
    prerelease = release.get("prerelease") is True
    pinging = ping and not prerelease
    lead = f"\U0001f4e6 **{name}** is out{' as a pre-release' if prerelease else ''}!"
    embed: Embed = {
        "title": name[:TITLE_CHARS],
        "url": url,
        "color": AMBER,
        "fields": [
            {
                "name": "Get it",
                "value": (
                    f"[Steam Workshop]({WORKSHOP}) {DOT} [GitHub release]({url}) "
                    f"{DOT} [Player's guide]({GUIDE})"
                ),
            }
        ],
        "footer": {"text": "Random New World"},
    }
    if opening := summary(_text(release, "body")):
        embed["description"] = opening
    if published := _text(release, "published_at"):
        embed["timestamp"] = published
    return {
        "content": f"<@&{PING_ROLE}> {lead}" if pinging else lead,
        "embeds": [embed],
        "allowed_mentions": {"parse": [], "roles": [PING_ROLE] if pinging else []},
    }


def load_release(path: Path) -> dict[str, object]:
    """The release object of a GitHub API answer or of a ``release`` event payload."""
    raw = cast("object", json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(raw, dict):
        msg = f"{path} does not hold a JSON object"
        raise TypeError(msg)
    data = cast("dict[str, object]", raw)
    release = data.get("release", data)
    if not isinstance(release, dict):
        msg = f"{path} has no release object"
        raise TypeError(msg)
    return cast("dict[str, object]", release)


def post(webhook: str, payload: Payload) -> None:
    """Send the message once, retrying when Discord asks to slow down or has a bad moment."""
    if not webhook.startswith(WEBHOOK_PREFIX):
        msg = f"the webhook must be a {WEBHOOK_PREFIX}... URL"
        raise ValueError(msg)
    request = urllib.request.Request(  # noqa: S310 - https only, checked above
        f"{webhook}?wait=true",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS):  # noqa: S310
                return
        except urllib.error.HTTPError as error:
            transient = error.code == TOO_MANY_REQUESTS or error.code >= SERVER_ERROR
            if not transient or attempt == ATTEMPTS:
                detail = error.read().decode(errors="replace")[:DETAIL_CHARS]
                msg = f"Discord answered {error.code}: {detail}"
                raise RuntimeError(msg) from error
            time.sleep(min(float(error.headers.get("Retry-After") or 2), MAX_WAIT_SECONDS))


class _Arguments(argparse.Namespace):
    release_file: Path = Path()
    dry_run: bool = False
    no_ping: bool = False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    _ = parser.add_argument("release_file", type=Path, help="release JSON or event payload")
    _ = parser.add_argument(
        "--dry-run", action="store_true", help="print the message, send nothing"
    )
    _ = parser.add_argument(
        "--no-ping", action="store_true", help="leave the Release Ping role out"
    )
    args = parser.parse_args(argv, namespace=_Arguments())
    try:
        payload = build_payload(load_release(args.release_file), ping=not args.no_ping)
    except (OSError, TypeError, ValueError) as error:
        print(f"discord_release: {error}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook:
        print("discord_release: DISCORD_WEBHOOK_URL is not set", file=sys.stderr)
        return 1
    try:
        post(webhook, payload)
    except (RuntimeError, ValueError, OSError) as error:
        print(f"discord_release: {error}", file=sys.stderr)
        return 1
    print(f"discord_release: announced {payload['embeds'][0]['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
