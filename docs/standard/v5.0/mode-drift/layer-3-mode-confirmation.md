# Layer 3 — Mode-Confirmation Audit Primitive

**Authority**: Mode-Drift mitigation Layer 3
**Status**: Fires at first use

---

## What Layer 3 Does

The Mode-Confirmation Audit primitive is an **interrupt at the `review-required` RECORD-state** in the dispatch state machine. It fires under three triggers:

1. **Layer 1 hard flag** — classifier-confidence ≥ 0.75 routes the record to the peer-reviewer queue (enforcement mode active from Week 7+ of the implementation lifecycle).
2. **Layer 2 audit-hook routing** — `Yes` or `Uncertain` on Q1-Q3, anything but `Yes` on Q4, a declined answer, or a Layer-1-vs-Layer-2 inconsistency.
3. **Explicit reviewer invocation** — the reviewer at `review-required` invokes the audit explicitly.

When fired, the primitive holds the record at `review-required` and routes to a designated human peer reviewer. The peer reviewer either:

- **Confirms** the Mode declaration → record proceeds to `closed` with reviewer disposition logged
- **Requests Mode 1 → Mode 2 migration** → Charter `mode_declaration` review by accountable owner; Charter amended OR record rolled back per migration trigger
- **Invokes Mode 2 → Mode 1 demotion** → record re-dispatches as Mode 1; `prior_state_archive` written with `demotion_path: 'audit-driven'`

## Peer-Reviewer Designation Rule (5 sub-rules)

Peer reviewer is named in the Charter's `peer_reviewer_pool` field, populated at Charter dispatch time.

1. **Substantive expertise**: peer reviewer must hold accountable_owner or equivalent role in a Charter operating in the same Decision Provenance Standard scope.
2. **Independence — author exclusion**: the peer reviewer for any given record MUST NOT be the original author of that record.
3. **Independence — Charter-owner exclusion when Charter owner authored**: if the Charter's `accountable_owner` authored the record under review, the Charter owner is excluded from the peer-reviewer slot for that record.
4. **Pool size minimum**: minimum 3 named individuals in `peer_reviewer_pool` to guarantee at least one eligible reviewer per record under exclusions 2 and 3. **Charters dispatching with a pool < 3 fail this requirement.**
5. **Conflict-of-interest carve-out**: a reviewer with material involvement in the record's substantive content (consulted on the decision, party to it, financially conflicted) recuses; queue routes to the next eligible pool member. Recusal logged in audit trail as a Layer 3 routing event.

The Charter owner is responsible for keeping `peer_reviewer_pool` current. Pool changes mid-Charter trigger a `peer_reviewer_pool_updated` audit-trail entry.

## Firing Authority for `no_silent_mode_drift_in_sample`

Layer 3 provides the named firing authority for the Level 2 conformance signal `no_silent_mode_drift_in_sample`. A peer-confirmed drift records a sample-level violation. Per the §4.8.2 emission cadence, the signal emits on Layer 3's audit cadence (15% rolling, with first-100 and edge-case overrides per Layer 1), **NOT on every dispatch transition** — this is what makes Layer 1's compute load tractable.

## State-Machine Integration

```
   review-required ──┬──> closed (peer-confirmed)
                     ├──> re-opened-with-mode-migration (Mode 1 → Mode 2 requested)
                     └──> re-opened-with-mode-migration (Mode 2 → Mode 1 demoted)
```

The §4.8.2 emission cadence governs how primitive outcomes emit to the conformance reporter.

## Triage SLA

Hard flags route to a single named queue per Charter, owned by the Charter's `accountable_owner` for triage and by a designated peer reviewer for the audit primitive itself. Triage SLA: **5 business days for hard flags from queue arrival to peer-reviewer disposition**. Beyond 5 days, the record auto-escalates to the Charter's escalation rule per Standard §3.2 → emits `POST /dps/conformance/charter-escalation` with `escalation_type: schedule_of_records_exception`.

## Reporter API Hand-off

Layer 3 emits Charter-level escalations to:

```
POST /dps/conformance/charter-escalation
```

Per the wire contract (`../conformance/reporter-api-spec.md`). Layer 3-specific `escalation_type` values:

- `layer_3_peer_review_demotion` — peer reviewer invoked Mode 2 → Mode 1 demotion
- `peer_reviewer_pool_underflow` — pool dropped below 3 mid-Charter
- `charter_escalation_rule_invoked` — auto-escalation past 5-day SLA

---

*Layer 3 fires at first use. Peer-review designation rule with pool minimum 3 + author/owner exclusions is the structural primitive that prevents single-actor capture of Mode classification authority.*
