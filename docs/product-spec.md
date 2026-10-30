# Product specification

Random New World generates New World geography and societies for EU5 while
preserving the vanilla Old World. The released 1.0.0 product is accepted by the
owner (C437); [roadmap](roadmap.md) separates its shipping scope from future work.

## Player journey

1. Get the standalone application or subscribe to the Workshop hub. In EU5 use
   **Open in folder** on Random New World and launch **Random New World Generator**.
2. Choose a landmass type and settings, or paste a World Code. Previews start
   covered; reveal the world only when wanted. The atlas supports geography,
   societies, resources and comparison.
3. Generate one local world mod. The application validates it and can install it
   into the profile. Enable that world in the playset and start a new 1337 campaign.
   The generator hub itself is not enabled. Keep the world's mod with its saves.
4. Reuse the code, export a compact world file, or reroll peoples/resources while
   retaining the land. A different algorithm epoch or changed game inputs can
   change regeneration; the application reports the distinction.

See the [guide](generator-guide.md) for operations and
[known limitations](known-limitations.md) for save and game compatibility.

## Shipping scope

- Five landmass archetypes, Random/Total Chaos choices, adjustable geography,
  continent sketches, optional drawn land and optional larger ocean canvas.
- Coherent relief, climate, biomes, rivers and sea geography from shared models.
- New location hierarchy, native countries and tribes, cultures, religions,
  demographics, economy and technology; optional extraordinary societies have
  geographic/social causes and trade-offs.
- Stories, formable countries, colonial names, exceptional resource places and
  explicit adaptations of vanilla content tied to the removed Americas.
- A desktop generator (Tauri window, classic Qt fallback), independent CLI, library, atlas, recovery, layer
  variants, portable mode, progress and cancellation.
- Player-visible text in every official language of the installed target build.

Actual control ranges and presets live in `settings.py` and `app/controls.py`;
this document does not invent a second list of presets or odds. Content definitions
are indexed by the [catalogue](content-catalog.md).

## Engineering requirements

Generate valid content at construction; reject failed invariants explicitly.
Preserve the Old World's pixels, identities and references. Derive visual layers
and gameplay templates from the same model. Keep generation deterministic across
supported platforms/thread counts under the recorded epoch and game inputs.
Use tests and reference exports as described in [testing](testing.md); preserve
the scope of engine observations without turning every research unknown into a gate.

Ship the generator and original/licensed assets; derive the built world on the
player's machine. Strength comes from land, population, technology and organization
rather than arbitrary superpower modifiers. Use vanilla mechanisms where they fit.
The accepted world-edge rendering limitation and deliberate optional selection
cover are described in the current architecture and limitations.

The [initial product proposal](archive/product-spec-initial.md) preserves early
control ideas and capability questions. They are historical design material.
