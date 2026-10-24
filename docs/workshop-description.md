# Workshop description

The Steam Workshop text for release 1.0.0 ([ADR 0009](adr/0009-hub-mod-with-generator.md)) is kept in Steam's own markup, ready to paste: [`workshop/english.bbcode`](workshop/english.bbcode) and one file per official language in [`workshop/`](workshop/). It is written for the player, as Workshop pages of EU5 mods are: what a world holds, a quick start, the choices of the window, why there is a program and what it does, the limits, a FAQ and the links. The design and the evidence live in the repository; the page links there.

Rules for the text:

- **Every statement holds for the published build.** Our notes for whoever uploads are in brackets, in English in every language (`[Until signed:]`, `[Confirm in 020.]`); they and the text they mark as conditional are settled and removed before upload ([release process](release-process.md)).
- **Steam's markup only**: `[h1]`, `[h2]`, `[b]`, `[i]`, `[list]`, `[olist]`, `[*]`, `[quote]`, `[url=…]`. Section headings carry one emoji each; Steam shows them as text.
- **8,000 bytes of UTF-8** per description, the closing NUL included ([Steamworks: ISteamRemoteStorage](https://partner.steamgames.com/doc/api/isteamremotestorage), `k_cchPublishedDocumentDescriptionMax`, accessed 2026-10-24). Cyrillic takes two bytes a letter and CJK three, so the Russian text is the tightest: it says the same as the English in fewer words.
- **The window's words for its controls and the game's for its interface** in every language (§2.9 of [localization](localization.md)): *Создать*, *Grundlagen*, *Condição de Jogo*, *播放集*, the game's name of Ironman. The mod list's titles stay English (C276), so the example name does too.
- **Translations follow the English.** Each translation starts with a line `source: <fingerprint>` naming the English it was made from; that line is ours and is not pasted. Change the English, then every translation, then the fingerprints. `tests/test_workshop.py` fails on a missing or outdated translation, on markup or links that differ from the English, on a lost note and on a text over the limit.
