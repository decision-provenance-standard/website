# Decision Provenance Standard&trade;

An open standard for audit-ready provenance of consequential decisions made by humans and AI systems together. The Standard defines a Charter object, a decision-record lifecycle, a disclosure block for AI-drafted content, and a self-declared conformance ladder, so that an organization can show how a decision was reached, who was accountable, and how the record was produced.

**Live site:** https://decisionprovenancestandard.org

## What the Standard is not

> The records are input, not evidence. The Standard informs frameworks without satisfying them. Conformance is self-declared; no body certifies it. It is not legal advice and not a regulatory substitute.

These limits are deliberate. A record produced under the Standard is structured input to the people who judge it — counsel, auditors, internal-controls officers, board fiduciaries — not, by its existence, legal evidence, certification, or attestation. The Standard's primitives map as an input substrate to regulatory and control frameworks; they inform that work without satisfying, replacing, or discharging any framework's obligations, which remain the deployer's.

## Repository structure

| Path | What it is | License |
|---|---|---|
| `docs/` | The published website (GitHub Pages source), including the Standard text, companions, glossary, FAQ, diagrams, and downloads. | CC-BY 4.0 |
| `docs/standard/v5.0/` | Reference files, release 5.1.1: JSON schemas, state machines, the conformance-signal list, the reporter contract and the test plan. | MIT |
| `tools/` | The build and check tools for the site. | Apache-2.0 |

The Standard does not depend on the reference files; the normative text is the Standard. Where the two differ, the text governs.

## License (by directory)

This repository is licensed by directory:

- **Standard text and website** — Creative Commons Attribution 4.0 International (CC-BY 4.0). See [`LICENSE`](LICENSE).
- **Reference files** under `docs/standard/v5.0/` — MIT License, for all of the 5.x line of reference releases. See [`docs/standard/v5.0/LICENSE`](docs/standard/v5.0/LICENSE).
- **Build and check tools** under `tools/` — Apache License 2.0. See [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt).

Etsion Brands Ltd claims "Decision Provenance Standard" as an unregistered trademark (&trade;). The licences cover the text and files, **not** the name; permitted uses of the name are set out in Standard §11.1. See [`NOTICE`](NOTICE).

## How to cite

See [`CITATION.cff`](CITATION.cff), or cite as:

> Etsion, Yohay. *Decision Provenance Standard*, version 1.1 (rev. 9). 2026. https://decisionprovenancestandard.org. Licensed CC-BY 4.0.

Version 1.0 (rev. 8) stays available unchanged at its original addresses, so citations of it still resolve.

## Stewardship

Founding Steward: Yohay Etsion. Institutional Steward: Etsion Brands Ltd.
