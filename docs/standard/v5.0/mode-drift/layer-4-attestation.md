# Layer 4 — Named Human-Attestation Fallback

**Authority**: Mode-Drift mitigation Layer 4
**Status**: Fires at first use — load-bearing for closing the silent-drift failure mode

---

## What Layer 4 Does

Closes the Mode-Drift safety net even when Layers 1-3 are silent. The `mode_classification_attestation` structured object on every closed decision record binds a named human (in their employed capacity) to the Mode classification and records the capacity in which they signed. The Standard makes no claim about how that capacity, or any indemnity a deployer offers, affects anyone's personal liability.

## Why Object, Not Scalar

A scalar field invites copy-paste — the attestor's name typed once, then duplicated across every record. An object forces every sub-field to populate at the moment of attestation: full name, role, employer, timestamp, jurisdiction, language version, verbatim signed text, capacity. Each field carries its own provenance burden; the structured form makes the attestation costly enough to be deliberate.

## Schema

See `layer-4-attestation.schema.json` for the JSON Schema Draft 2020-12 binding.

Eight required fields:

| Field | Purpose |
|---|---|
| `attestor_full_name` | Legal name as on employment record |
| `attestor_role_title` | Role title at attestation moment |
| `attestor_employer` | Legal entity employing the attestor |
| `attestation_timestamp` | ISO 8601 UTC — system-stamped, NOT user-editable |
| `jurisdiction` | enum: US-DE \| US-FED \| UK \| EU \| IL \| OTHER |
| `attestation_language_version` | Captures variant in force at attestation time |
| `attestation_text_signed` | Verbatim — preserves the version actually signed |
| `attestor_capacity` | enum: employee \| contractor \| officer \| director |

## Verbatim Attestation Language (U.S. base)

> "I, [attestor_full_name], in my capacity as [attestor_role_title] at [attestor_employer], confirm that I have reviewed the substantive content of this decision record and that the Mode classification recorded in its metadata accurately reflects the substantive role of AI worker output in framing the options under consideration. I make this confirmation in my employed capacity on behalf of [attestor_employer], and not in a personal capacity. This confirmation is made for the purpose of internal Decision Provenance Standard conformance and does not constitute legal advice or legal certification."

## Jurisdictional Variants

| Jurisdiction | Variant clause |
|---|---|
| U.S. (Federal + Delaware) | Base language above. |
| UK (England & Wales) | Replace "in my employed capacity ... not in a personal capacity" with "in the course of my employment by [attestor_employer], acting within the scope of my duties." |
| EU | Base language above. |
| Israel | Replace "employed capacity" with "במסגרת תפקידי" (within the scope of my role). |

Deployers may adapt the wording to local practice with their own advisers. The wording above is an example only, not checked for any jurisdiction.

## Evidence the Attestor Signs Onto

The attestation references the Layer 2 challenge-prompt answers as substantive evidence: the attestor reviews the four logged answers (Q1-Q4 from Layer 2's audit hook) on the record before signing. Layer 2 audit-trail fields (`answers`, `routing_decision`, and where applicable `subsequent_layer_3_outcome`) are the evidentiary base.

The attestor signs onto the proposition that **given those four answers and any Layer 3 resolution**, the recorded Mode classification accurately reflects the substantive role of AI worker output.

## Implementation Notes

- `attestation_timestamp` is server-stamped at the moment the structured object is committed to the decision record. Client-side timestamps are rejected (422 if attempted).
- `attestation_text_signed` is the verbatim text presented to the attestor at the moment of attestation. If the attestation language is later revised, the revised text carries a new `attestation_language_version`, and prior records retain the version they signed (no retroactive rewriting).
- The 200-character minLength on `attestation_text_signed` prevents accidentally short/empty attestation submissions.
- Email is NOT captured here. Email lives in the broader system audit log, decoupled to avoid creating the appearance of a personal commitment by individual email address.

---

*Layer 4 closes the silent-drift failure mode at first use. The structured-object form is what makes the attestation deliberate.*
