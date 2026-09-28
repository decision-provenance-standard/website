# Conformance Signal Vocabulary — v5.1.2

**Authority**: Standard §6
**Status**: 1:1 binding to the `evidence_metric` enum in the reporter API. 23-signal vocabulary across Levels 1, 2, 3.
**Naming**: `dps_conformance_signal` in code; "Decision Provenance Standard conformance signal" in prose

---

## Overview

The signal vocabulary is the named, machine-readable surface that Section 6 reads to grade a Charter or decision record at Conformance Levels 1, 2, or 3. Every signal:

- Has a single named firing authority (which actor or state machine emits it)
- Has a defined cadence (per-record, per-Charter, sample-level, on-demand)
- Has a binding to one of the locked `evidence_metric` enum values in the reporter API
- Records process; **does NOT certify**, ensure, or substitute for regulator/auditor review

---

## Level 1 Signals (Charter Structural Completeness)

| Signal | Firing authority | Cadence | When emitted |
|---|---|---|---|
| `charter_state_is_fields_completed` | Charter state machine | Per-Charter | Transition into `fields-completed` |
| `mode_declaration_populated` | Charter state machine | Per-Charter | Transition out of `open` |
| `schedule_of_records_committed` | Charter state machine | Per-Charter | Transition into `fields-completed` |
| `record_location_resolvable` | Charter state machine | Per-Charter | Validation: URL or path resolves on transition into `fields-required` |
| `accountable_owner_named` | Charter state machine | Per-Charter | At `open` (validation: reference resolves to a single named human) |
| `re_decision_triggers_minimum_met` | Charter state machine | Per-Charter | Validation: ≥1 outcome trigger + ≥1 market trigger on transition into `fields-required` |

## Level 2 Signals (Decision-Record Discipline)

| Signal | Firing authority | Cadence | When emitted |
|---|---|---|---|
| `every_record_carries_mode_declaration` | Decision-record state machine | Per-record | Transition into `closed` (validation: `dispatch_mode` populated) |
| `every_mode_2_record_has_disclosure_block` | Decision-record state machine | Per-record (Mode 2, within the §4.6 requirement) | Transition into `closed` |
| `every_mode_1_edge_case_record_has_disclosure_block` | Decision-record state machine | Per-record (Mode 1 + edge case, within the §4.6 requirement) | Transition into `closed` |
| `disclosure_block_required_fields_populated` | Decision-record state machine | Per-record | Validation: the five disclosure-block fields (Standard §4.6.2) all populated |
| `no_silent_mode_drift_in_sample` | **Layer 3 Mode-Confirmation Audit primitive** | Sample-level (NOT per-record) | Per the §4.8.2 emission cadence — Layer 3 audit cadence (15% rolling, with first-100 + edge-case overrides) |
| `every_affirmed_record_carries_affirmation_event` | Decision-record state machine | Per-record (at `affirmed`) | Validation: `affirmation_record` populated with timestamp + actor identity + method per §5.1(3) |
| `every_affirmed_record_carries_seal_hash` | Decision-record state machine | Per-record (at `affirmed`) | Validation: `seal_hash` populated per §5.1(3) |
| `no_passive_promotion_to_affirmed_in_sample` | **Layer 3 / sample-audit primitive** | Sample-level per the §4.8.2 emission cadence | Audits a sample of `affirmed` records for compliance with §5.2 affirmation-is-an-affirmative-human-act requirement |
| `every_redaction_event_carries_operational_store_deletion_attestation` | Decision-record state machine / sample-audit | Sample-level per the §4.8.2 emission cadence | Reads field population of `operational_store_deletion_attestation` (4 sub-fields); substantive correctness is for the deployer to determine |
| `every_mode_2_record_carries_drafting_authority` | Decision-record state machine | Per-record (at `affirmed`, Mode 2) | Validation: `drafting_authority.deployer_role_pointer` populated per §6.2.3 |
| `altitude_to_consent_posture_binding_enforced` | Access-policy layer / sample-audit | Sample-level | Audits `altitude: individual-professional` records for consent-posture binding per §6.2.3.1 |

A Level 2 signal that reads records of a kind the Charter does not yet have does not apply until the Charter has one (Standard §7.3, "When there is nothing yet to check").

## Level 3 Signals (Continuously Auditable)

| Signal | Firing authority | Cadence | When emitted |
|---|---|---|---|
| `escalation_rule_records_present_when_invoked` | Decision-record state machine | On-demand | When Charter `escalation_rule` fires AND a corresponding decision record exists |
| `disclosure_review_cadence_current` | Disclosure metadata state machine | Per-Charter (Mode 2) | When each disclosure block was reviewed within the cadence the Charter declares: a current `last_reviewed_at`, or a disclosure-review record naming the record (Standard §7.4.1) |
| `schedule_of_records_queryable` | Conformance reporter | On-demand | When schedule export endpoint returns 200 OK with valid response |
| `conformance_level_reporter_output_recent` | Conformance reporter | On-demand | When most-recent reporter output within freshness threshold |
| `re_decision_triggers_firing_on_schedule` | Charter state machine | Every state transition + scheduled reporter run | When re-decision trigger evaluation runs per Charter cadence (Level 3 per §7.4.2) |
| `superseded_records_retained_in_full` | Conformance reporter | On-demand / every-transition | Validation: superseded records remain in schedule, immutable; current record carries `supersedes` reference per §5.1(3) |

## Sample Audit-Cadence Binding for Layer 3

`no_silent_mode_drift_in_sample` (Level 2) emits on the following cadence:

| Charter type | Audit cadence | First-100 override |
|---|---|---|
| Standard Mode-1 Charter | 15% rolling sample of closed Mode-1 records | Until Charter has 100 closed records, audit every record |
| `mode-1-with-embedded-mode-2-summary` Charter | 30% rolling sample | Same first-100 override |
| Charter on Layer 1 enforcement mode (Week 7+) | 15% baseline + 100% of Layer 1 hard-flag records | Same first-100 override |

The cadence is what makes Layer 1's compute load tractable AND what gives Layer 3 firing authority for the signal. Without this cadence binding, the signal would be either uncomputable (audit every record at scale) or non-firing (no defined triggering event).

---

## Reporter API Binding

The signal vocabulary above is **the locked enumeration** for the `evidence_metric` field in `POST /dps/conformance/charter-escalation` request payload. Free-text values rejected with `400 invalid_evidence_metric`.

See `reporter-api-spec.md` for the wire contract and `reporter-api.openapi.yaml` for the OpenAPI 3.1 binding.

---

## Cross-Stream Conformance Check

The cross-stream test apparatus walks a synthetic Charter library (per `../tests/synthetic-charter-library.md`) through full lifecycle states, asserting that:

1. Each emitted signal corresponds to a Standard section structural requirement
2. Each Standard section structural requirement has a corresponding emitted signal
3. The locked `evidence_metric` enum is the union of all signals emitted by the state machines

A round-trip mismatch (the Standard says X, the implementation emits Y) is the failure mode the cross-stream check exists to catch.

---

## Language Discipline Enforcement

This vocabulary **records process**, **NOT** evidence. Writing about these signals MUST use:

- "The signal **records** that the schedule of records is queryable" (✅)
- NOT "The signal **proves** the schedule of records is queryable" (✗)
- "Conformance reporter **emits** the signal" (✅)
- NOT "Conformance reporter **certifies** the signal" (✗)

---

*Signal vocabulary at v5.1.2 (23 signals: 6 Level 1, 11 Level 2, 6 Level 3). Amendments require steward review.*
