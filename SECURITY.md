# Security policy

Random New World is a program that players run on their own machines. It reads the EU5 installation and writes mods into the game's profile folder, and its Windows build ships a launcher and an embedded Python runtime. We take reports about it seriously.

## Supported versions

The latest stable release receives security fixes. Fixes also go to `main`, which is a development branch rather than a supported release. Older stable versions and historical 0.x builds are unsupported unless an explicit maintenance line is announced.

| Version | Supported |
|---|---|
| Latest stable (1.0.0 at first publication) | ✅ |
| Earlier stable / 0.x | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for a security problem.** Report it privately in one of these ways:

- **GitHub:** use [*Report a vulnerability*](https://github.com/Sir-Starch/eu5-random-new-world/security/advisories/new) on the repository's *Security* tab;
- **E-mail:** starch@sirstarch.com, with `[RNW security]` in the subject.

Include the version, your platform, steps to reproduce, and the impact you expect. If you attach a diagnostics file (`rnw diagnostics-file`), read it first; it is redacted, but you decide what you share.

This is a volunteer project. We aim to acknowledge a report within **7 days** and to agree on a fix and a disclosure date with you. Credit is given in the advisory unless you prefer otherwise.

## Scope

In scope:

- the generator writing, deleting or overwriting files **outside** its data folder and the world mods it creates (`mod/rnw_exp_world_*` and their library entries);
- path traversal, unsafe archive extraction or code execution through **world codes, `.rnworld` / `.rnworld-mod` files**, or other input a player might receive from someone else;
- the Windows launcher, the embedded runtime and its import path, or a packaged build that differs from its tagged source;
- any network access by the generator, which is designed to have none;
- personal data that leaks through logs or the diagnostics file despite its redaction.

Out of scope:

- bugs and crashes in Europa Universalis V itself (report them to Paradox on the [official forum](https://forum.paradoxplaza.com/));
- a generated world that fails to load or play. That is an ordinary bug, so please [open an issue](https://github.com/Sir-Starch/eu5-random-new-world/issues/new/choose);
- antivirus or SmartScreen warnings about unsigned builds. Code signing is planned ([ADR 0009](docs/adr/0009-hub-mod-with-generator.md)).

## Supply chain

Release artifacts are built by the [release workflow](.github/workflows/release.yml) from a pinned candidate commit or its matching version tag. Python dependencies are locked with hashes in `uv.lock`, and Rust dependencies in `native/Cargo.lock`. The Windows build uses the official embeddable CPython, pinned by SHA-256. The release workflow checks that no game assets end up in a package.
