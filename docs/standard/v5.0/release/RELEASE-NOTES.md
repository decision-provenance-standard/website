# Reference Files — Release Notes

**Release label**: v5.1.1
**Directory path**: `standard/v5.0/` (unchanged so the Standard's `standard/v5.0/...` references resolve; v5.1.1 is the version label, the path stays `v5.0/`)
**Aligned to**: Decision Provenance Standard, version 1.1 (reading edition rev. 9)

---

## Release 5.1.1 (2026-09-28), with version 1.1 of the text (reading edition rev. 9)

A correction release. The reference files are brought into line with the corrected text; nothing a validator or a reporter checks has changed.

- **Unchanged:** the structure of every JSON schema (properties, required fields, types, allowed values and patterns), the OpenAPI reporter contract (byte for byte) and the names of the 23 signals. Only description strings and prose changed.
- **Changed wording:**
  - The files are described as "reference files" (schemas, state machines, the signal list, the reporter contract and a test plan), not as a working implementation; internal names, draft notes and internal codes are removed.
  - Descriptions no longer say when a law applies or what it requires; that is for the deployer to determine.
  - `mode-drift/`: sections 4.8.1 to 4.8.3 of the text are the normative statement of the mode-drift layers, and these files describe them; the text governs where they differ. The Layer 2 route is stated as the text states it (DR-2026-0004): `Yes` or `Uncertain` on Q1-Q3, anything but `Yes` on Q4, a declined answer, or a Layer 1 / Layer 2 mismatch routes the record to Layer 3. The Layer 4 attestation no longer tells signers where their personal liability sits.
  - The signal-list footer gives the correct count: 23 signals, 6 Level 1, 11 Level 2, 6 Level 3.
  - Conformance is described as self-declared by the adopting organization, as the text says (Section 7), not by the implementer.
- **Still open:** the differences between the text and these files that the repository's `tests/known-defects/` lists (KD-01 to KD-09) are not fixed in this release; they are held for release 5.2.0. KD-08 and KD-09 were added to that list during the work on this release.
- **Release 5.1.0 stays recoverable** at tag `rev8-published`.
- **Licence:** MIT, as for all of 5.x.

The text's own release notes, including what changed in version 1.1, are in the repository's root `README.md`.

---

## What This Release Is

This release holds the machine-readable reference files for the Decision Provenance Standard: schemas, state machines, the signal list, the reporter contract and a test plan. They follow the Standard's normative text; where they differ, the text governs. Differences found so far are listed in the repository's `tests/known-defects/`.

The reference files describe how process is recorded. They do not certify, ensure, or substitute for any regulator or auditor review. Conformance to the Standard is self-declared by the adopting organization; no body certifies it.

---

## What It Contains

- **23-signal conformance vocabulary** — Level split: 6 Level 1 (Charter structural completeness) + 11 Level 2 (decision-record discipline) + 6 Level 3 (continuously auditable). The vocabulary is the locked enumeration the reporter API validates `evidence_metric` against, identical between `conformance/signal-vocabulary.md` and the OpenAPI `evidence_metric` enum.
- **3-value `dispatch_mode` enum** — `mode-1`, `mode-2`, `mode-1-with-embedded-mode-2-summary`. Exhaustive; no fourth mode.
- **5-field Article 50 disclosure schema** — `declaring_authority`, `ai_system_identity`, `jurisdictional_applicability`, `content_type_tag`, `generation_timestamp`, plus permitted implementation extras tolerated by the conformance check. The schema also requires `disclosure_text_pointer` and `attached_at`, seven fields in all, where the text requires five (known defect KD-06; see "Still open" above).
- **Mode-drift four-layer composed mitigation** — Layer 1 statistical detection (detection-only scaffolding at first release), Layer 2 in-flow 4-question audit hook (hard gate at Mode-1 record close), Layer 3 Mode-Confirmation Audit primitive (peer-review confirmation), Layer 4 named human attestation (structured `mode_classification_attestation` object at close).
- **Two state machines** — Charter 5-state forward-only lifecycle + `review-required` RECORD-state interrupt; decision-record `dispatched / drafted / closed` lifecycle with the two deliberately-distinct §5.1-lifecycle and §6.2-dispatch state families.
- **Reporter API** — single-write `POST /dps/conformance/charter-escalation` endpoint (OAuth 2.0 client_credentials, idempotency-key, synchronous ack-only, standardized error envelope, rate limiting, JSON Schema Draft 2020-12 validation).
- **Cross-stream conformance test apparatus** — synthetic Charter library + category test matrix asserting 1:1 alignment between the Standard's normative text and the reference files.

---

## Versioning

This release carries the label **v5.1.1**. The directory path remains `standard/v5.0/` so the Standard's `standard/v5.0/...` references resolve; the version label and the directory path are deliberately distinct. Conformance-contract changes (signal vocabulary, schema field names, reporter wire contract) are additive at the schema and enum level and follow semantic-version discipline; breaking changes to the contract require a major-version bump and steward review.

---

## Licensing

The Decision Provenance Standard text is licensed CC-BY 4.0. These reference files are licensed MIT.

---

## Earlier releases

- **Release 5.1.0**, with version 1.0 of the text (reading edition rev. 8, dated 2026-05-30): the first release of these files. It is kept, unchanged, at tag `rev8-published`.

---

*Reference files aligned to the Decision Provenance Standard, version 1.1 (reading edition rev. 9).*
