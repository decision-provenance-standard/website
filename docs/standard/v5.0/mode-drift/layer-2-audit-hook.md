# Layer 2 — In-Flow Audit Hook (4-Question Challenge)

**Authority**: Mode-Drift mitigation Layer 2
**Status**: Fires at first use — at every Mode-1 record close as a hard gate

---

## What Layer 2 Does

Surfaces a 4-question Substantive-Authorship Challenge to the declaring authority at the moment a Mode-1-declared record transitions from `drafted` to `closed`. `Yes` or `Uncertain` on Q1-Q3, anything but `Yes` on Q4, a declined answer, or a Layer-1-vs-Layer-2 inconsistency routes the record to Layer 3 at `review-required` and blocks `closed`. A record that closed before v1.1 (reading edition rev. 9) keeps the route recorded with it (`routing_decision`, with the `challenge_prompt_version` shown); the route above applies to records that close under v1.1 (reading edition rev. 9) or a later release.

## The 4 Questions (verbatim)

> **Q1**: Did AI worker output materially shape the options framing presented to you in this record?
>
> **Q2**: Did AI worker output materially shape the recommended option, the rejected options, or the comparative-evaluation criteria?
>
> **Q3**: Did AI worker output draft prose that is reproduced verbatim or near-verbatim in the substantive content of this record?
>
> **Q4**: If you removed all AI worker contributions from your working materials, would the record's substantive conclusion remain unchanged?

Q1-Q3 escalate from framing → recommendation → prose. Q4 is the **counterfactual trap question** — surfaces the latent-influence case where the human believes they "made the call" but cannot reconstruct it without the AI worker output.

## Attestation Language (verbatim)

> "I, the declaring authority for this record, attest that to the best of my knowledge as of {timestamp} my answers to the four Mode-1 Substantive-Authorship Challenge questions are accurate. I understand that a 'Yes' or 'Uncertain' answer on any of Q1-Q3, or a 'No' or 'Uncertain' answer on Q4, is a material indication that this record may be Mode 2 rather than Mode 1, that this record will be routed to Layer 3 peer review, and that mis-attestation is a Standard-conformance violation that the Charter's named human-attestation field (Layer 4) ultimately binds me to."

When this language is revised, implementations present the revised text under a new `challenge_prompt_version`; each record keeps the `challenge_prompt_version` and the verbatim `attestation_text` it was shown.

## Routing Logic

| Trigger | Route |
|---|---|
| **Any non-`No` on Q1-Q3** (i.e., `Yes` or `Uncertain` to "did AI shape your work?") OR **non-`Yes` on Q4** | Route to Layer 3 at `review-required` |
| Declaring authority declines to answer | Treated as Q4 = `Uncertain` → Route to Layer 3 |
| Layer-1-vs-Layer-2 inconsistency (Layer 1 flagged Mode 2 candidate; Layer 2 answered all clean) | Route to Layer 3 |

## 10-Field Audit Trail

For every fire of the hook, the `layer_2_audit_trail` object on the decision record captures (per `../schemas/decision-record.schema.json`):

`record_id`, `declaring_authority {name, role, organization}`, `challenge_prompt_version` (semver), `answers` (4-element array of enum), `timestamp_presented`, `timestamp_answered`, `attestation_text`, `routing_decision`, `routing_rationale`, `layer_1_flag_state {flagged, classifier_version, corpus_version, confidence}`, `subsequent_layer_3_outcome` (backfilled when Layer 3 resolves).

## Single Jurisdictional Set

The four questions are about substantive authorship-of-record, not regulatory thresholds. The latent-influence drift problem is the same across U.S./EU/UK/Israel. No jurisdictional variants — adding them would create an arbitrage surface (a deployer with multi-jurisdiction operations would default to whichever set is most permissive). Jurisdiction-specific attestation wording is handled by Layer 4, not Layer 2.

## Why Hard Gate at Close

Layer 2 is a **hard gate**, not advisory. Before the dispatch state machine accepts a `closed` transition for a Mode-1-declared record, the hook MUST fire AND collect 4 valid answers AND record the audit trail AND make the routing decision. A declaring authority who declines or attempts to bypass the gate cannot transition the record to `closed`.

This is what prevents the silent drift failure mode: a record cannot quietly close as Mode 1 if the declaring authority's answers (or refusal to answer) indicate AI worker substantive contribution.

---

*Layer 2 fires at first use. The 4-question structure + 10-field audit trail + identity-bound attestation give Layer 4 the evidentiary base it signs onto.*
