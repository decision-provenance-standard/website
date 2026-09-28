# Decision Provenance Standard — Reference Files

Machine-readable reference files for the Decision Provenance Standard: schemas, state machines, the signal list, the reporter contract and a test plan. They also describe the mode-drift four-layer composed mitigation that the Standard's conformance language refers to.

> The records are input, not evidence. The Standard informs frameworks without satisfying them. Conformance is self-declared; no body certifies it. It is not legal advice and not a regulatory substitute.

**Standard text is licensed CC-BY 4.0. These reference files are licensed MIT.**

---

## What This Directory Is

This directory holds the machine-readable reference files the Standard's normative text points to:

- A **23-signal conformance vocabulary** across Levels 1, 2, and 3.
- A **single-write conformance reporter API** (Charter-level escalation events).
- A **mode-drift four-layer composed mitigation** (statistical detection, in-flow audit hook, peer-review confirmation, named human attestation).
- **JSON Schemas** (Draft 2020-12) for the Charter object, the decision-record object, the disclosure block, and the Layer 4 attestation object.
- Two **state machines** (Charter lifecycle, decision-record lifecycle).
- A **cross-stream conformance test apparatus** plus a synthetic Charter library.

The reference files describe how process is recorded. They do not certify, ensure, or substitute for any regulator or auditor review. Conformance to the Standard is self-declared by the adopting organization; no body certifies it.

---

## Bundle Contents

| Path | Purpose |
|---|---|
| `state-machines/charter-state-machine.md` | Charter 5-state forward-only lifecycle + `review-required` RECORD-state interrupt (Standard §3) |
| `state-machines/decision-record-state-machine.md` | Decision-record `dispatched / drafted / closed` lifecycle (Standard §5) |
| `schemas/article-50-disclosure-metadata.json` | The five required disclosure-block fields (`declaring_authority`, `ai_system_identity`, `jurisdictional_applicability`, `content_type_tag`, `generation_timestamp`) + permitted implementation extras (Standard §4.6) |
| `schemas/charter.schema.json` | Charter object schema (JSON Schema Draft 2020-12) |
| `schemas/decision-record.schema.json` | Decision-record object schema (JSON Schema Draft 2020-12) |
| `conformance/reporter-api-spec.md` | `POST /dps/conformance/charter-escalation` contract |
| `conformance/reporter-api.openapi.yaml` | OpenAPI 3.1 wire contract |
| `conformance/signal-vocabulary.md` | 23-signal vocabulary across Levels 1, 2, 3 (6 L1 + 11 L2 + 6 L3) + audit-cadence binding |
| `mode-drift/layer-1-detection.md` | Statistical detection scaffolding |
| `mode-drift/layer-2-audit-hook.md` | 4-question challenge prompt at decision-record close |
| `mode-drift/layer-3-mode-confirmation.md` | `review-required` RECORD-state interrupt + peer-review designation |
| `mode-drift/layer-4-attestation.md` + `layer-4-attestation.schema.json` | `mode_classification_attestation` structured object (named human attestation) |
| `tests/cross-stream-conformance-check.md` | Conformance test apparatus |
| `tests/synthetic-charter-library.md` | Synthetic Charters for round-trip verification |
| `release/RELEASE-NOTES.md` | Release notes for the reference files |

---

## Mode-Drift Mitigation

The mode-drift mitigation closes the silent Mode 1 → Mode 2 drift failure mode because three of its four layers fire at first use:

- **Layer 2** (in-flow audit hook) fires at every Mode-1 record close as a hard gate.
- **Layer 3** (Mode-Confirmation Audit primitive) fires on routed records.
- **Layer 4** (named human-attestation) fires at close with a structured object schema.

Layer 1 (statistical detection) ships as detection-only scaffolding; its enforcement gates phase in on a multi-week cadence after first release (see `mode-drift/layer-1-detection.md`). The composition of Layers 2, 3, and 4 closes the drift failure mode at first use; Layer 1 adds population-level signal once its corpus is complete.

---

## Conformance Signal Coverage

The 23-signal vocabulary maps the Standard's structural requirements to named, machine-readable signals:

| Level | Count | Scope |
|---|---|---|
| Level 1 | 6 | Charter structural completeness |
| Level 2 | 11 | Decision-record discipline |
| Level 3 | 6 | Continuously auditable |

The vocabulary is the locked enumeration the reporter API validates the `evidence_metric` field against. See `conformance/signal-vocabulary.md`.

---

## Directory Path Note

The directory name is `v5.0/` and is kept unchanged so the Standard's `standard/v5.0/...` references resolve. The reference-files release label is v5.1.2 (see `release/RELEASE-NOTES.md`); the directory path stays `v5.0/`.

---

## Naming Convention

Human-facing prose names the Standard in full: **"Decision Provenance Standard."** In code identifiers, API endpoint paths, and file-system namespaces, the prefix `dps` is used (`dps_conformance_signal`, `/dps/conformance/...`).

---

## Stewardship

**Founding Steward**: Yohay Etsion. **Institutional Steward**: Etsion Brands Ltd.

Amendments to the conformance contract (signal vocabulary, schema field names, reporter wire contract) require steward review.

---

*Reference files aligned to the Decision Provenance Standard. Standard text CC-BY 4.0; reference files MIT.*
