from __future__ import annotations

import subprocess
from unittest.mock import Mock

import pytest
import window


@pytest.mark.parametrize("tool", ["npm", "npx"])
def test_windows_node_batch_tools_run_through_cmd(tool: str) -> None:
    command = [tool, "--version"]
    assert window.platform_command(command, windows=True) == [
        "cmd.exe",
        "/d",
        "/s",
        "/c",
        subprocess.list2cmdline(command),
    ]


def test_non_windows_node_tools_run_directly() -> None:
    command = ["npm", "ci", "--prefer-offline"]
    assert window.platform_command(command, windows=False) == command


def test_cargo_metadata_is_read_as_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = (
        '{"packages": [], "resolve": {"root": "root", "nodes": [{"id": "root", "deps": []}]}}'
    )
    run = Mock(return_value=subprocess.CompletedProcess([], 0, stdout=metadata))
    monkeypatch.setattr(subprocess, "run", run)

    assert window.crates() == []
    assert run.call_args.kwargs["encoding"] == "utf-8"
