# Cross-Stream Conformance Check — Test Apparatus

**Status**: v5.0

---

## What This Check Does

Walks a synthetic Charter library (`synthetic-charter-library.md`) through full lifecycle states, asserting field-for-field alignment between:

1. **Standard normative text** (Sections 3, 4, 5, 6) — what the Standard says the Charter should carry, transit, and emit
2. **Reference files** (state machines, schemas, signal list) — what the reference files define

A round-trip mismatch is the failure mode the check exists to catch. The check is what makes the claim that this directory matches the Decision Provenance Standard's text structurally defensible: without the apparatus the claim is unsupported; with it, the alignment is demonstrable.

---

## Test Categories

### Category A — Charter Lifecycle Round-Trip

For each synthetic Charter in the library:

1. Instantiate Charter at `open` with required minimum fields per Standard §3
2. Walk through state transitions: `open → mode-declared → fields-required → fields-completed`
3. At each transition, assert:
   - Standard §3 required fields are populated per the field schema
   - State machine emits the expected Level 1 conformance signals
   - The reporter API would accept a Charter-level escalation under this Charter (auth + payload validation)
4. Walk through `closed` transition; assert closure timestamp + preservation of decision records

### Category B — Decision-Record Lifecycle Round-Trip

For each Charter in `fields-completed`:

1. Dispatch a decision record (Mode 1)
2. Walk: `dispatched → drafted → closed`
3. At `closed`, assert:
   - Layer 2 audit hook fired with 4 questions captured
   - Layer 4 `mode_classification_attestation` populated with all 8 required sub-fields
   - Level 2 signals (`every_record_carries_mode_declaration`, etc.) emitted
4. Repeat for Mode 2 with disclosure metadata block populated
5. Repeat for `mode-1-with-embedded-mode-2-summary` edge case with per-record disclosure attachment

### Category C — Layer 2 Hard Gate

1. Dispatch Mode 1 record
2. At `drafted → closed` transition, present 4-question challenge with answers triggering routing to Layer 3
3. Assert: record state holds at `review-required`, NOT `closed`
4. Assert: `layer_2_audit_trail` populated with all 10 required fields
5. Repeat with declined-answer pathway → assert routed to Layer 3
6. Repeat with Layer-1-vs-Layer-2 inconsistency pathway → assert routed to Layer 3

### Category D — Layer 3 Mode Confirmation

1. Hold record at `review-required`
2. Apply each peer-reviewer disposition: confirm, request migration, invoke demotion
3. Assert state transitions match decision-record state machine
4. Assert `prior_state_archive` populated on demotion with `demotion_path` enum
5. Assert `peer_reviewer_pool_underflow` escalation emitted when pool drops below 3

### Category E — Layer 4 Attestation

1. At `closed`, assert `mode_classification_attestation` required and populated
2. Validate against schema (`../mode-drift/layer-4-attestation.schema.json`)
3. Assert verbatim attestation text matches jurisdictional variant per `attestation_language_version`
4. Assert `attestation_timestamp` is server-stamped (not client-supplied)
5. Test all 4 jurisdictional variants (US, UK, EU, IL)

### Category F — Reporter API Wire Contract

1. POST charter-escalation with valid payload → 201 + expected response shape
2. POST with invalid `evidence_metric` → 400 with `error_code: invalid_evidence_metric`
3. POST with missing `Idempotency-Key` → handled per dedup window logic
4. POST with replayed `Idempotency-Key` + identical body → server returns original response verbatim
5. POST with replayed `Idempotency-Key` + divergent body → 409 with `error_code: idempotency_key_reuse_with_divergent_body`
6. POST with `escalation_type: layer_1_*` AND missing `classifier_metadata` → 400
7. POST exceeding rate limit → 429 with `Retry-After` header + `retry_after` field
8. Validate field-pair semantics (timestamp/window, type/metric, threshold/operator/value/observed)

### Category G — Signal Vocabulary 1:1 Binding

For every signal in `../conformance/signal-vocabulary.md`:

1. Assert signal name appears in OpenAPI `evidence_metric` enum
2. Assert signal has a defined firing authority (state machine or layer)
3. Assert signal can be triggered by the synthetic Charter library
4. Assert no signal in the OpenAPI enum is missing from `signal-vocabulary.md` (no orphaned enum values)

### Category H — Naming Convention Compliance

1. Scan all human-facing artifacts (README, release notes, reader-facing prose, schema `title`/`description` metadata) for the names of internal projects, products or authoring tools in prose contexts
2. Assert "Decision Provenance Standard" full spelling used in all reader-facing prose
3. Assert `dps` is the prefix retained in: API endpoint paths, code identifiers, file-system paths
4. Failure: any internal project, product or authoring-tool name in reader-facing prose, OR any residual project-specific code-path prefix

### Category I — Standard ↔ Reference-File Field Alignment

1. For each field in Standard §3 Charter schema → assert corresponding field in `charter.schema.json`
2. For each field in the Standard's §4.6.2 disclosure block → assert corresponding field in `article-50-disclosure-metadata.json`
3. For each field in Standard §5 decision-record schema → assert corresponding field in `decision-record.schema.json`
4. For each Section 6 conformance Level criterion → assert at least one signal in vocabulary corresponds

**Field-name normalization note (v5.1.0 reconciliation).** When matching the text's field name (prose display name) to the schema's JSON key, the check normalizes:

- **Hyphen ↔ underscore**: the text uses hyphenated display names (`declaring-authority`); the schemas use snake_case JSON keys (`declaring_authority`). These are the same binding identifier under the two serialization conventions the Standard explicitly blesses (§3.2: "Field names are the binding identifiers; serializations may be JSON, YAML, typed objects… so long as the field semantics align"; §6.2.4: "Field names are binding; type names are illustrative"). Normalize hyphen ↔ underscore before comparing.
- **Trailing `-tag` display suffix**: tolerate a trailing `-tag` on the text's display name when the JSON key omits it (`jurisdictional-applicability-tag` ↔ `jurisdictional_applicability`).

**Permitted extra fields.** The check matches the Standard-required fields against the schema; additional schema fields are permitted extras and do NOT fail the check. For the disclosure block, the five Standard-required fields are `declaring_authority`, `ai_system_identity`, `jurisdictional_applicability`, `content_type_tag`, `generation_timestamp`; `disclosure_text_pointer`, `attached_at`, `mode_1_edge_case_flag`, `last_reviewed_at`, `disclosure_provenance` are permitted extras.

**Two state families (decision record).** The check verifies BOTH families exist (per the decision-record state machine's "Two State Families" note): the §6.2 dispatch states on `record_state`, and the §5.1 lifecycle (`draft`/`reviewed`/`affirmed`) expressed via `affirmation_record`/`seal_hash` population. It does NOT require a single normalized enum and does NOT flag the two-family design as a divergence.

---

## GO Verdict

The check produces a binary GO / NO-GO verdict:

- **GO** — every category passes; the alignment claim is structurally defensible
- **NO-GO** — any category fails; the claim must be downgraded or the release blocked

---

*Test apparatus for the reference files.*
