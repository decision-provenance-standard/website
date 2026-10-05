# Charter State Machine — v5.0 Reference File

**Authority**: Standard §3 (Charter Mechanism)
**Naming**: "Decision Provenance Standard" full spelling in prose; `dps_charter_state` in code identifiers
**Status**: v5.0 reference file

---

## States (5 forward-only + 1 RECORD-state interrupt)

```
       ┌────────────────────────────────────────────────────────────┐
       │                                                            │
       │   open ──> mode-declared ──> fields-required ──>           │
       │                                                            │
       │              fields-completed ──> closed                   │
       │                                                            │
       │                                                            │
       │   review-required (RECORD-state interrupt; not Charter-state)
       │                                                            │
       └────────────────────────────────────────────────────────────┘
```

The Charter lifecycle is **forward-only**. There is no transition from `closed` back to any prior state; a closed Charter that needs reactivation is a new Charter with a back-pointer.

`review-required` is **not** a Charter-state. It is a RECORD-state interrupt that fires on a single decision record while the Charter remains in `fields-completed`. Modeling `review-required` as a Charter-state would imply that the entire Charter halts on a single drift flag.

---

## State Transition Table

| From | To | Required for transition |
|---|---|---|
| (creation) | `open` | `charter_id`, `charter_name`, `decision_class`, `accountable_owner` populated |
| `open` | `mode-declared` | `mode_declaration` populated with one of: `mode-1`, `mode-2`, `mode-1-with-embedded-mode-2-summary` |
| `mode-declared` | `fields-required` | `inside_decisions`, `outside_decisions`, `cadence`, `record_location`, `re_decision_triggers` (≥1 outcome + ≥1 market evidence trigger), `escalation_rule` populated |
| `fields-required` | `fields-completed` | `schedule_of_records`, `conformance_level_declared` populated. If `mode_declaration` ∈ {`mode-2`, `mode-1-with-embedded-mode-2-summary`}: `disclosure_metadata_pointer` populated. `peer_reviewer_pool` is recommended, not required: the text (Standard §3.2, §3.3) sets neither the field nor a pool size, so a Charter without one, or with fewer than 3 named individuals, does not fail this check. A pool of 3 or more is recommended, so that the Layer 3 designation rule leaves an eligible reviewer for every record. If any record under this Charter describes a natural person below executive altitude: `use_case_scope_limit_declaration` populated (Standard §3.1). In EU/UK works-council jurisdictions where altitude is function-leader or below: `works_council_consultation_record` populated (Standard §3.1). |
| `fields-completed` | `closed` | Decision-class subsumption, organizational dissolution, or explicit closure event. `closed_at` timestamp set. |

Forward-only enforcement: a Charter in `fields-completed` cannot regress to `fields-required` even if a field is later cleared. The fix is a new Charter version (Charter `v2`) with `prior_charter_ref` back-pointer.

---

## Required Mode-Declaration Field

`mode_declaration` is **required at any state past `open`**. The dispatch state machine refuses to authorize any decision under a Charter still in `open`. This is the structural primitive that catches the unauthored-Mode-2 failure mode (Standard §3 §3.4).

The enum is exhaustive — no fourth mode. Any drafter or implementer believing a fourth mode is needed raises it as an issue or pull request (GOVERNANCE.md), never a runtime workaround.

---

## RECORD-state Interrupt: `review-required`

When fired (Layer 1 hard flag; Layer 2 audit-hook routing on `Yes` or `Uncertain` on Q1-Q3, anything but `Yes` on Q4, a declined answer, or a Layer-1-vs-Layer-2 inconsistency; Layer 3 explicit invocation; or Charter `escalation_rule` invoked), the affected decision record holds at `review-required` and routes to a designated peer reviewer (per `peer_reviewer_pool` + Layer 3 designation rule).

The Charter itself remains in `fields-completed`. Other records under the same Charter continue dispatching normally.

Outputs from `review-required`: `closed` (peer reviewer confirms Mode), `re-opened-with-mode-migration` (peer reviewer requests Mode 1 → Mode 2 migration or Mode 2 → Mode 1 demotion).

---

## Wire Format Reference

See `../schemas/charter.schema.json` for the JSON Schema Draft 2020-12 binding.

---

## Conformance Signal Emissions

This state machine emits the following Level 1 signals (per `../conformance/signal-vocabulary.md`):

- `charter_state_is_fields_completed` — fires on transition into `fields-completed`
- `mode_declaration_populated` — fires on transition out of `open`
- `schedule_of_records_committed` — fires on transition into `fields-completed`
- `record_location_resolvable` — fires on transition into `fields-required` (validation: URL or path resolves)
- `accountable_owner_named` — fires at `open` (validation: reference resolves to a single named human)
- `re_decision_triggers_minimum_met` — fires on transition into `fields-required` (validation: ≥1 outcome trigger + ≥1 market trigger)

---

*Forward-only lifecycle. The RECORD-state interrupt model preserves Charter-level continuity under per-record drift detection.*
