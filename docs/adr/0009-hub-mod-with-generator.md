# ADR 0009: Deliver the generator through one Workshop hub

**Status:** Accepted 2026-10-21; implementation shipped in 1.0.0.
Consolidated 2026-10-29 without changing the delivery architecture. Supersedes
the delivery proposals in ADRs 0004 and 0008. ADR 0007's Qt choice remains current;
ADR 0010 adds independent operation, layers, world files and recovery.

## Decision

One free Workshop item carries the generator. The player uses EU5's **Open in
folder** and runs **Random New World Generator** as a separate application.
The public item is **Random New World (RNW)**, ID **`sirstarch.randomnewworld`**.
The maintained local folder stays **`rnw_exp_hub`**; the updater recognises its
former internal ID for safe updates (C438).

The hub contains no gameplay content and need not be enabled in a playset.
The generator reads the local game installation and creates one self-contained
world mod. That world carries all its gameplay scripts, settings and content;
the player enables it and keeps it for its saves. No companion/probe mod is needed.
The built world is local and is excluded from public distribution.

Windows/Proton delivery uses the official embeddable Python, locked runtime
wheels, the project package, a small launcher and `_native.pyd`. Native Linux
application archives are also offered. PyInstaller remains the native/development
packaging tool; it is not the Windows hub delivery mechanism. The current window
uses Qt. The [roadmap](../roadmap.md) records a future Tauri design request.

The application also works independently of Workshop. Its library is in the
platform's normal application data directory, or a user-selected/portable folder.
A Workshop installation reuses that local library; it does not download worlds
with the hub. The actual downloaded 3,272-file hub matches the prepared upload
and includes no library/world files (C441).

## Runtime and trust

The application reads the game without modifying it, requests no administrator
rights, makes no network requests and writes only its data and selected world-mod
outputs. Official runtimes may contain networking modules; their presence is not
a claim that the generator uses the network. Installation and archive boundaries
are checked in tests and package audits.

The project launcher and native extension are unsigned. That is a disclosed,
accepted 1.0.0 limitation: Smart App Control may block execution. Signing can be
added later without reopening release acceptance or requiring an account action
from the agent. A VirusTotal result describes the exact file scanned, including
unsupported/failed engines, and is not a signature or a universal safety verdict.
Unchanged binaries reuse the same report.

Owner Windows 11 and Linux/Proton runs, package self-tests, tagged Linux/Windows
CI and downloaded release checks establish the shipping delivery evidence
(C428, C438–C439, C441). They do not make claims about every OS security configuration
or all game mechanics. [Known limitations](../known-limitations.md) records that scope.

## Publication and alternatives

[Release process](../release-process.md) owns build/tag/checksum/publication steps.
[Legal notes](../legal.md) own the reviewed distribution and dependency boundary.
No new blanket clearance or whole-library antivirus scan is required for the
unchanged hub; investigate concrete new issues when they arise.

DLL injection, engine patching and a finite pool of pregenerated worlds were
rejected as the delivery architecture. Their original investigation and source
citations are preserved in [delivery design history](../archive/delivery-design-2026-10.md).
