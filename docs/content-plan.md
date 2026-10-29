# New World content

N0–N5 are implemented and included in the accepted 1.0.0 product (C437).
The exporter adapts content that refers to the Americas to generated geography
and societies. It also supplies original stories, formations and colonial names.
The [catalogue](content-catalog.md) describes player content; the generated
[reference](content-reference.md) lists definitions in detail.

## One decision for every vanilla consumer

`content_inventory.py` inventories references to replaced American keys/tags.
`content_decisions.py` decides each object: keep, rebind, neutralize or replace.
`content_check.py` stops export on an undecided required consumer;
`content_report.py` provides the report. The table stores identifiers and decisions,
not redistributed vanilla scripts. `eu5_content.py`, `eu5_remap.py` and related
writers apply them locally from the installed game.

The 1.4.5 / Across the Pillars audit found 655 consumers, including 19 newly
requiring decisions; 0.13.22/epoch 59 supplies them (C426–C427). New patches need
an updated inventory rather than a blanket assumption that all new objects work.
The [compatibility audit](research/compatibility-1-4-5.md) holds exact dispositions
and limits of runtime observations.

## Generated stories and formations (N2–N4)

`content.py` plans content eligibility for each world's states; `storymodel.py`
defines scripts, graphs and pulse checks. `stories.py`, `stories_n4.py` and
`stories_colonial.py` hold the story families. `formations.py` and
`colonial_names.py` define formables and names. `eu5_story.py`, `eu5_formation.py`
and `eu5_places.py` write their game records.

Keep vanilla mechanisms where they express the feature. All scripts and hooks
belong to the generated world, never an enabled companion/probe mod. Conditions
and outcomes must resolve against the actual generated geography and societies;
validate references, localization and graph consistency at construction.

## Geography keys chosen for content (N5)

Generated regions and land areas reuse the needed vanilla identities through
physical matching within their original hierarchy, rather than taking arbitrary
positional identity. The [N5 audit](research/n5-region-keys.md) records the
matching policy and all positional consumers. `hierarchy.py` and the New World
exporter construct and verify the hierarchy. Preserve the Old World and treat
content meaning as part of generation, not a repair layer over already-written output.

## Changes and verification

A new story, family or compatible option normally belongs in MINOR; compatible
corrections belong in PATCH. Use the release-level rules of
[ADR 0003](adr/0003-versioning.md), affected goldens and a pending world epoch
when nonmetadata world files change. Translate affected player text into the
official languages and update catalogue/reference output where definitions change.

Synthetic content tests and read-only installed-game checks establish written
syntax, dispositions, references and deterministic output. Owner sessions and logs
establish their own observed engine behavior. Historical per-family unknowns are
research scope, not a demand to rerun every story before each change; use the
[current verification workflow](testing.md).

The [original implementation plan](archive/content-implementation-plan-0.x.md)
preserves the gap analysis, stage breakdown, hook experiments and final-audit
checklists. Its per-commit versioning and pending 0.x acceptance instructions are
superseded by the current release policy and owner acceptance.
