# Reference Files — Release Notes

**Release label**: v5.2.0
**Directory path**: `standard/v5.0/` (unchanged so the Standard's `standard/v5.0/...` references resolve; v5.2.0 is the version label, the path stays `v5.0/`)
**Aligned to**: Decision Provenance Standard, version 1.3 (reading edition rev. 11)

---

## Release 5.2.0 (2026-10-05), with version 1.3 of the text (reading edition rev. 11)

A minor release (DR-2026-0020 in the repository's `governance/decisions/`). The reference files now accept what the text accepts. Of the eleven differences between the text and the files listed at release 5.1.2, ten are fixed; KD-01 stays open.

- **Fixed in the decision-record schema** (contributed in pull requests #11, #12 and #13):
  - KD-02: a record that omits `record_type` is no longer treated as a redaction event. An omitted `record_type` means a decision, as the text says.
  - KD-03: the redaction fields follow the table in Standard §6.2.3. `redaction_basis` accepts the text's 13 values in the text's spelling; `redaction_basis_detail` is required, and must not be empty, only for `other_named_statute` and `deployer_initiated_under_regulatory_order`; `redaction_authority` and `operational_store_deletion_attestation` accept the text's shapes. The earlier hyphenated values and the earlier shapes stay accepted and are marked deprecated. They can be removed only in a major release.
  - KD-05: `altitude` is required from the `drafted` state onward, as the text requires. A missing `altitude` no longer shows up as an unrelated `consent_posture` error.
  - KD-07 and KD-10: the schema no longer requires `disclosure_metadata_pointer` on every Mode 2 record, which it did from `dispatched` and even for outputs a Charter places outside the disclosure requirement. Whether a record needs the pointer depends on the Charter (Standard §4.6.1), which a schema cannot see, so the new signal checks it (KD-04, below).
- **Loosened to match the text:**
  - Disclosure block (KD-06): only the five fields of Standard §4.6.2 are required. `disclosure_text_pointer` and `attached_at` are optional. The jurisdiction and content-type tags accept the text's spellings (`eu`, `us-federal`, `us-delaware`, `uk`, `israel`, `other:<...>`), and every earlier spelling stays valid.
  - Declaring authority (KD-08): a value that names only the person (`full_name`) or only the organization (`employer`) is valid. A value that names no one is still rejected.
  - Peer-reviewer pool (KD-09): the Charter schema accepts a pool of one or more named people. The Charter state machine and the Layer 3 designation rule recommend three instead of failing a smaller pool. The `peer_reviewer_pool_underflow` escalation value is unchanged.
  - Counsel of record (KD-11): a Charter may carry the recommended `named_employment_counsel_of_record` field (Standard §3.1). A field the schema does not list is still rejected.
- **Added (KD-04):** the Level 2 signal `every_mode_2_record_carries_disclosure_pointer`, in the signal list and the OpenAPI `evidence_metric` enum, with its test vectors in the repository's `tests/reporter-signals/`. It checks the disclosure pointer from `drafted` onward on Mode 2 records and on records with an embedded AI-drafted summary, within the disclosure requirement. The vocabulary has 24 signals: 6 Level 1, 12 Level 2, 6 Level 3. The reporter contract's version moves from 1.1.0 to 1.2.0 (an additive change; see its amendment log).
- **Changed wording:** `reporter-api-spec.md` points to `reporter-api.openapi.yaml` for the request schema instead of carrying a copy. The copy listed `soft_flag_rate_breach`, which is not a signal and was never in the OpenAPI enum, so nothing is renamed or removed from the binding contract. No `evidence_metric` value is fixed for `layer_1_soft_flag_rate_breach`. The directory README gives the 24-signal count.
- **One shape now rejected:** a record at `drafted` or later that has no `altitude` but carries `consent_posture` validated under 5.1.2 and is rejected now (KD-05). The text has required `altitude` from the draft state in every published edition, so no record that met the text is affected.
- **Compatibility:** apart from that case, every record and Charter that validated under 5.1.2 still validates. Checked with a structural diff of every schema and by re-validating every case and record in the repository.
- **Still open:** KD-01. The decision-record schema refers to the attestation schema by an address that a validator working from the files alone cannot resolve. The files are unchanged.
- **Release 5.1.2 stays recoverable** at tag `ref-5.1.2`.
- **License:** MIT, as for all of 5.x.

The fixes for KD-02 to KD-05, KD-07 and KD-10, and the new signal with its test vectors, were contributed by Laurent Lemonnier, iSoluce.

The text's own release notes, including what changed in version 1.3, are in the repository's root `README.md`.

---

## Release 5.1.2 (2026-09-28), with version 1.2 of the text (reading edition rev. 10)

A wording release with version 1.2 of the text. The reference files follow v1.2's clarifications.

- **Unchanged:** the structure of every JSON schema (properties, required fields, types, allowed values and patterns), the OpenAPI reporter contract (byte for byte) and the names of the 23 signals. Only description strings and prose changed.
- **Changed wording:**
  - The Mode 1 row of the decision-record state machine still carried the old Layer 2 closing rule, which release 5.1.1 missed; it now states the route the text states (Standard §4.8).
  - Disclosure review can be shown by `last_reviewed_at` or by a disclosure-review record (Standard §7.4.1), and the disclosure checks name the exclusion of §4.6.1.
  - Descriptions no longer call the disclosure block an "Article 50" block, and no longer say who decides a deployer's legal questions.
- **Still open:** KD-01 to KD-11 in the repository's `tests/known-defects/`, held for release 5.2.0. KD-10 and KD-11 were added during the work on this release.
- **Release 5.1.1 stays recoverable** at tag `ref-5.1.1`.
- **License:** MIT, as for all of 5.x.

The text's own release notes, including what changed in version 1.2, are in the repository's root `README.md`.

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

- **24-signal conformance vocabulary** — Level split: 6 Level 1 (Charter structural completeness) + 12 Level 2 (decision-record discipline) + 6 Level 3 (continuously auditable). The vocabulary is the locked enumeration the reporter API validates `evidence_metric` against, identical between `conformance/signal-vocabulary.md` and the OpenAPI `evidence_metric` enum.
- **3-value `dispatch_mode` enum** — `mode-1`, `mode-2`, `mode-1-with-embedded-mode-2-summary`. Exhaustive; no fourth mode.
- **5-field disclosure-block schema** — `declaring_authority`, `ai_system_identity`, `jurisdictional_applicability`, `content_type_tag`, `generation_timestamp`, plus permitted implementation extras tolerated by the conformance check. `disclosure_text_pointer` and `attached_at` are optional extras; the schema requires the text's five fields only.
- **Mode-drift four-layer composed mitigation** — Layer 1 statistical detection (detection-only scaffolding at first release), Layer 2 in-flow 4-question audit hook (hard gate at Mode-1 record close), Layer 3 Mode-Confirmation Audit primitive (peer-review confirmation), Layer 4 named human attestation (structured `mode_classification_attestation` object at close).
- **Two state machines** — Charter 5-state forward-only lifecycle + `review-required` RECORD-state interrupt; decision-record `dispatched / drafted / closed` lifecycle with the two deliberately-distinct §5.1-lifecycle and §6.2-dispatch state families.
- **Reporter API** — single-write `POST /dps/conformance/charter-escalation` endpoint (OAuth 2.0 client_credentials, idempotency-key, synchronous ack-only, standardized error envelope, rate limiting, JSON Schema Draft 2020-12 validation).
- **Cross-stream conformance test apparatus** — synthetic Charter library + category test matrix asserting 1:1 alignment between the Standard's normative text and the reference files.

---

## Versioning

This release carries the label **v5.2.0**. The directory path remains `standard/v5.0/` so the Standard's `standard/v5.0/...` references resolve; the version label and the directory path are deliberately distinct. Conformance-contract changes (signal vocabulary, schema field names, reporter wire contract) are additive at the schema and enum level and follow semantic-version discipline; breaking changes to the contract require a major-version bump and steward review.

---

## Licensing

The Decision Provenance Standard text is licensed CC-BY 4.0. These reference files are licensed MIT.

---

## Earlier releases

- **Release 5.1.2**, with version 1.2 of the text (reading edition rev. 10, dated 2026-09-28): kept, unchanged, at tag `ref-5.1.2`.
- **Release 5.1.1**, with version 1.1 of the text (reading edition rev. 9, dated 2026-09-28): kept, unchanged, at tag `ref-5.1.1`.
- **Release 5.1.0**, with version 1.0 of the text (reading edition rev. 8, dated 2026-05-30): the first release of these files. It is kept, unchanged, at tag `rev8-published`.

---

*Reference files aligned to the Decision Provenance Standard, version 1.3 (reading edition rev. 11).*
