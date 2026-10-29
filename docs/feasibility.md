# Capability overview

The project implements the external **T3** route: new New World geography,
location identities, hierarchy, physical fields, societies and content are
written as a complete local EU5 mod. This is the released RNW 1.0.0 product,
accepted by the owner (C437), rather than an unproven geography proposal.
[Architecture](architecture.md) maps its implementation.

| Route | Current role |
|---|---|
| T0: political/demographic changes on fixed geometry | Diagnostic concept; not the product goal |
| T1/T1.5/T2: attribute, class and existing-boundary changes | Useful historical experiments and D0 tooling; not a fallback required before T3 |
| T3: generated topology and societies in the New World | Shipping implementation |
| T4: whole-world regeneration | Outside the product scope: preserve the Old World |
| T5: mutate geography while EU5 is running | Not implemented; not needed for the external generator |

A changed EU5 patch still requires checking the actual installed input contract;
that does not invalidate observed behavior on a recorded earlier build. Specific
limits are in [known limitations](known-limitations.md), and forward work is in
[roadmap](roadmap.md).

The [1.4.1 feasibility investigation](archive/feasibility-1.4.1.md) preserves the
original hypothesis matrix, alternatives, early failed access tests and later
wrap correction. Its statement that no tier had yet been observed describes the
2026-10-13 research stage, not the current product.
