from __future__ import annotations

import subprocess

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
