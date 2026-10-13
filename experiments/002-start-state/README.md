# 002 — one-location start-state change

- **Hypothesis:** A mod can change an American location's starting owner, culture or pops while retaining vanilla geometry.
- **Method:** Select a low-coupling location from `definitions.txt`; make one minimal setup override with a uniquely observable value; validate its syntax against 1.4.1 local files; compare complete vanilla and mod logs; inspect the 1337 start state in game. Do not replace broad setup files until file-level override semantics are known.
- **Files/tools:** `game/main_menu/setup/1337/21_locations.txt`, `06_pops.txt`, `10_countries.txt`, local hierarchy, `rnw logdiff`.
- **Game version:** Target 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** Not prepared or launched. No in-game observation [UNKNOWN C13].
- **Remaining uncertainty:** Override precedence, partial/full file replacement, start-state validation, visual verification.
- **Architecture implication:** Gates T0 and all later political generation; do not assume syntax alone works.
- **Status:** **NOT-RUN**. The owner requested no additional EU5 launches this session after experiment 001's unresponsive first-run screen.
