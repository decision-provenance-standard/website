# Conformance Reporter API Contract — POST /dps/conformance/charter-escalation

**Status**: Locked at v1.2
**Spec version**: 1.2.0 (matches OpenAPI YAML `info.version`)
**Cross-references**: Standard §6 (signal vocabulary); Mode-Drift mitigation Layer 3 (audit-cadence binding)

---

> This file is a reference wire contract for the Decision Provenance Standard's conformance reporter. The records are input, not evidence. The Standard informs frameworks without satisfying them. Conformance is self-declared; no body certifies it. This file is not legal advice and not a regulatory substitute.

---

## Endpoint

```
POST /dps/conformance/charter-escalation
```

**Purpose.** Single-write endpoint by which a deployer-side Conformance Reporter emits a Charter-level escalation event (Layer-1 soft-flag-rate breach, Layer-2 audit-hook breach, Layer-3 peer-review demotion, Layer-4 attestation refusal, or Charter `escalation_rule` invocation per Standard §3.2) into the Standard's escalation surface. The endpoint records process; it does not certify a Charter as compliant or grade conformance level. Grading is the conformance-level reporter's separate read surface (out of scope for this contract).

**Bound to the Standard.** §3 Charter state model (`charter_id`, `escalation_rule`); §6 conformance-signal vocabulary (the signals of `signal-vocabulary.md`, which the `evidence_metric` enum in `reporter-api.openapi.yaml` lists one for one, are the fixed enumeration the field validates against); Mode-Drift mitigation Layer 3 audit-cadence binding (escalation events emitted by the peer-review primitive use this endpoint).

---

## 1. Auth Model

**Choice: Deployer-side OAuth 2.0 client_credentials flow (RFC 6749 §4.4) over TLS 1.3.**

- Token endpoint: `POST /dps/oauth2/token` (separate from this contract).
- Scope required on access token: `conformance:write`.
- Bearer presented in `Authorization: Bearer <token>` header.
- Token TTL: 1 hour. Refresh via re-issuance against client_credentials (no refresh token — short TTL acceptable because escalation traffic is bursty + low volume).
- Client identity (`client_id`) MUST be provisioned per deployer organization, never per Charter. Deployers may emit escalations for any Charter whose `accountable_owner` is registered under the deployer's `client_id`.

**Rationale.**

1. **API keys rejected** because (a) static keys leak silently and Charter-escalation events carry `accountable_owner` identity that should not be implicitly bound to a leaked credential, and (b) client_credentials gives the deployer a structural rotation path without re-provisioning the Charter binding.
2. **Deployer-side, not user-side.** The Reporter is a deployer-operated component running inside the deployer's environment; it asserts the deployer's own identity, not an end-user's. User-delegated flows (authorization_code) would couple Charter-level events to individual end-user sessions, which is the wrong granularity.
3. **TLS 1.3 not negotiable.** Lower TLS versions rejected at the listener.

**Rejected alternative.** Static `Authorization: ApiKey <key>` was considered for simplicity. Rejected because the Layer-4 named-attestor binding upstream depends on identity-bound provenance that survives credential rotation; static keys conflate "rotated last week" with "different deployer," which corrupts the audit trail.

---

## 2. Idempotency

**Required header on every POST: `Idempotency-Key: <uuid-v4>`.**

- The `Idempotency-Key` is generated client-side by the Reporter, scoped to the deployer + Charter + escalation event.
- Server retains the `(client_id, Idempotency-Key)` tuple for **24 hours** in a dedup cache.
- On replay within the window with identical request body hash → server returns the original response (status code, body, headers) verbatim. No side effects.
- On replay within the window with **divergent** request body hash → server returns `409 Conflict` with `error_code: idempotency_key_reuse_with_divergent_body`. This catches the Reporter-bug case where the same `Idempotency-Key` accidentally attaches to two distinct events.
- Beyond 24 hours, the same `Idempotency-Key` is treated as fresh (deployers MUST NOT rely on cross-day dedup; the SLO is one operational day).

**Server-side request-hash dedup window.** Independent of `Idempotency-Key`, server hashes `(client_id, charter_id, escalation_type, evidence_window_start, evidence_window_end, escalation_timestamp)` and rejects identical hash within **5 minutes** as `409 Conflict` with `error_code: duplicate_escalation_in_dedup_window`. This catches Reporter retry storms where the client forgot to set `Idempotency-Key`.

**Retry semantics.** Reporters MUST retry on 5xx + 429 with exponential backoff (initial 1s, factor 2, max 60s, max 6 attempts). Reporters MUST NOT retry 4xx (except 429); 4xx responses indicate a contract violation that retrying does not resolve.

---

## 3. Response Shape

**Choice: Synchronous ack-only.** No async pattern; no `status_url`; no polling.

**Success response (201 Created):**

```json
{
  "escalation_id": "esc_01HXYZ...",
  "charter_id": "ch-pmm-positioning-lock",
  "accepted_at": "2026-05-12T14:33:18.421Z",
  "received_signals": ["no_silent_mode_drift_in_sample"],
  "schema_version": "v1.0"
}
```

- `escalation_id`: server-generated stable identifier (ULID), opaque to the Reporter; used by the conformance-level reporter's read surface to back-reference the event into the schedule of records.
- `accepted_at`: server timestamp of acceptance (ISO 8601 with milliseconds, UTC).
- `received_signals`: echoes the conformance signals (per Standard §6) that the server parsed from `evidence_metric`. Any unrecognized signal in the request is rejected at validation (§4 below) — this echo is for the Reporter's own audit trail.
- `schema_version`: pinned `v1.0` for the lifetime of this contract.

**Rationale.** Async with status URL was rejected because:
1. The escalation event is itself a recorded process artifact; it is NOT a long-running computation. The server's only work is validate + persist + acknowledge.
2. Async forces the Reporter to maintain polling state and re-attach the result to its own audit trail, which adds a class of "lost-poll" failure modes the sync contract does not have.
3. The cross-stream conformance check walks synthetic Charters and verifies escalation events round-trip; sync makes that test deterministic in a single request.

The endpoint is bounded to ≤ 500ms p99 server-side. If a deployer's Reporter cannot accept a 500ms blocking call, the Reporter should batch escalations into its own background queue and call this endpoint from the queue worker (the deployer's design choice, not this contract's concern).

---

## 4. Error Semantics

**Standardized error envelope (every 4xx + 5xx response):**

```json
{
  "error_code": "invalid_evidence_metric",
  "error_message": "evidence_metric 'mode_certified_compliant' is not a recognized conformance signal. Reference Standard §6.",
  "error_field": "evidence_metric",
  "retry_after": null,
  "trace_id": "trc_01HXYZ...",
  "schema_version": "v1.0"
}
```

| Status | When | `error_code` examples | `retry_after` |
|---|---|---|---|
| 400 Bad Request | Malformed JSON, missing required field, schema-validation failure (per §6 below) | `invalid_evidence_metric`, `missing_required_field`, `malformed_json`, `unknown_escalation_type` | null |
| 401 Unauthorized | Missing / expired / malformed bearer token | `token_missing`, `token_expired`, `token_malformed` | null |
| 403 Forbidden | Token valid but `client_id` not authorized for the asserted `charter_id` (Charter `accountable_owner` not registered to this deployer) | `charter_not_owned_by_client`, `scope_insufficient` | null |
| 409 Conflict | Idempotency-key reuse with divergent body; duplicate escalation within 5-minute server-side dedup window | `idempotency_key_reuse_with_divergent_body`, `duplicate_escalation_in_dedup_window` | null |
| 422 Unprocessable Entity | Request structurally valid but semantically inconsistent (e.g., `escalation_timestamp` later than `evidence_window_end`; `evidence_threshold` outside the metric's defined range) | `timestamp_outside_evidence_window`, `evidence_threshold_out_of_range`, `escalation_type_metric_mismatch` | null |
| 429 Too Many Requests | Per-deployer token bucket exhausted (per §5) | `rate_limit_exceeded` | seconds (integer) until next refill |
| 500 Internal Server Error | Server fault; persistence failure | `internal_error` | null |
| 502 Bad Gateway | Upstream persistence layer unreachable | `persistence_unreachable` | null |
| 503 Service Unavailable | Maintenance window or graceful degradation | `service_unavailable` | seconds (integer) |

**Error envelope discipline.**
- `trace_id` MUST be present on every error response so the deployer can correlate against server-side logs without exposing internal log identifiers.
- `error_message` is human-readable but stable per `error_code` (Reporters may match on `error_code`, never on `error_message` substring).
- `retry_after` populated only on 429 + 503; null elsewhere (NOT zero — null signals "do not retry on this error class").

---

## 5. Rate Limiting

**Per-deployer token bucket.**

- **Default**: 60 escalations per minute, burst 120 (token bucket capacity 120, refill 1 per second).
- **Override mechanism**: per-`client_id` rate-limit override is a server-side configuration; deployers request increases via the deployer-onboarding ticket process (out of band — not exposed via API). The override request requires (a) a Charter-count justification (deployers with > 50 active Charters typically need a higher floor) and (b) a Layer-1 soft-flag rate forecast (deployers with high anticipated drift detection need higher burst).
- **Override ceiling**: 600/min, burst 1200. Above the ceiling, the deployer's traffic shape suggests Reporter misconfiguration or batch-emit anti-pattern — IT-governance review required before further increase.

**Bucket scope.** `client_id`, NOT `(client_id, charter_id)`. A deployer with a noisy Charter does not consume rate-limit budget that a different deployer would otherwise have.

**429 behavior.** Server returns `Retry-After: <seconds>` as both an HTTP header and the `retry_after` field in the error envelope (redundant by design; Reporters parse whichever they prefer). The seconds value is the time until the bucket has at least 1 token, rounded up.

**Rationale.** 60/min is well above the expected steady-state escalation rate for a single deployer (Layer-1 hard flags are bounded by 5%-of-records-sampled-at-15%; Layer-2 hook breaches and Layer-3 peer-review demotions are bursty but low-volume). The 120 burst handles end-of-cadence batches (e.g., a deployer's monthly Charter audit firing many escalations in a window). Above 600/min, the Reporter is probably emitting one event per record rather than aggregated Charter-level escalations, which violates the contract's intent.

---

## 6. Request Payload Schema

**Content-Type: `application/json`. UTF-8.**

The request body is the `CharterEscalationRequest` schema in [`reporter-api.openapi.yaml`](reporter-api.openapi.yaml) (`components.schemas.CharterEscalationRequest`). That file is the binding wire contract. This section does not copy it, so the two cannot drift apart: the `escalation_type` values, the `evidence_metric` values (the signals of [`signal-vocabulary.md`](signal-vocabulary.md), one for one), the required fields and each field's type are read from the OpenAPI file.

What the OpenAPI file does not say in words:

- `charter_id`: the Charter's stable identifier (Standard §3.2).
- `evidence_metric`: one named signal from the vocabulary. Free-text values are rejected.
- `escalation_timestamp`: when the Reporter detected the escalation. It must fall in the window the field-pair checks below give.
- `accountable_owner_ref`: a reference to the Charter's `accountable_owner` (Standard §3.2). The server verifies that the reference resolves and that the accountable owner is registered under the asserted `client_id`.
- `narrative`: optional context from the Reporter, at most 2000 characters. Shown to peer reviewers; never authoritative.
- `linked_record_ids`: optional ids of the decision records the escalation pertains to, at most 200. For larger sets, emit a Charter-level escalation and link the schedule export.
- `classifier_metadata`: required when `escalation_type` starts with `layer_1_` (Layer 1 corpus-version provenance, Standard §4.8.1).

**Validation strictness.** `additionalProperties: false` at every object level. Unknown fields rejected with `400 unknown_field`. The conformance signal enumeration in `evidence_metric` is the contract's tightest binding to Standard §6 — any signal not in the enum is a contract violation, not a pass-through.

**Field-pair semantic checks (422-class):**
- `escalation_timestamp` MUST satisfy `evidence_window.start ≤ ts ≤ evidence_window.end + 24h` (24h grace allows post-window detection).
- `escalation_type` and `evidence_metric` MUST be a recognized pair. The pair this contract names: `schedule_of_records_exception` → `schedule_of_records_queryable` or `every_record_carries_mode_declaration`. For `layer_1_soft_flag_rate_breach` the contract names no pair: the soft-flag rate is not one of the signals, so any `evidence_metric` value in the enum is accepted with it. A mismatch with a named pair returns `422 escalation_type_metric_mismatch`.
- `evidence_threshold.operator` + `value` + `observed` MUST yield a true comparison consistent with the threshold being breached (e.g., if `operator=gt`, `value=0.05`, `observed=0.07` is consistent; `observed=0.03` is inconsistent → `422 evidence_threshold_not_breached`).

---

## Open Questions for Implementation

The lock above fixes the wire contract. The following items are deliberately left to implementation judgment, with named bounds:

1. **Persistence layer choice**: append-only event log vs. relational + audit-trigger pattern. Either acceptable provided the `(escalation_id, accepted_at)` tuple is stable and queryable by `client_id` and `charter_id` from day one. The cross-stream conformance walk reads via a separate read API (out of scope for this contract).
2. **`trace_id` format**: ULID, UUID v4, or W3C `traceparent`-derived. Implementer may pick; the only binding is opacity and stability per request.
3. **OAuth client_credentials issuer co-location**: same service or separate identity-provider service. Either acceptable; the bearer-token validation contract is the same.
4. **Layer-1 `classifier_metadata` schema versioning**: this contract pins `classifier_version` + `corpus_version` as opaque strings. The internal taxonomy of those strings is a Layer-1 implementation concern (Mode-Drift mitigation Layer 1 corpus provenance) and may evolve without breaking this contract.
5. **`narrative` indexing strategy**: full-text vs. metadata-only. Indexing choice is downstream; the field is delivered to peer-reviewer surfaces via the read API.
6. **Webhook fan-out**: whether a consumer subscribes to escalation events via a separate webhook or polls the read API. Out of scope for this contract; both patterns can be layered atop the persisted event log.

Items NOT preserved (locked): everything in §§1-6 above. Deviations require a contract amendment under steward review, NOT a runtime workaround.

---

## Cross-References

- **Standard §3.2** — Charter state model; `charter_id`, `accountable_owner`, `escalation_rule` field semantics.
- **Standard §6** — Conformance-signal vocabulary; the `evidence_metric` enum is bound 1:1 to this section's signal names.
- **Mode-Drift mitigation Layer 1** — Statistical detection; `classifier_metadata.classifier_version` + `corpus_version` provenance.
- **Mode-Drift mitigation Layer 3** — Audit-cadence binding; `escalation_type: layer_3_peer_review_demotion` is the canonical Layer 3 surface for this endpoint.

---

*Wire contract locked at v1.2.0.*

---

## Amendment Log

### v1.1.0

**Change**: Added `peer_reviewer_pool_underflow` to the `escalation_type` enum (now 9 values, previously 8).

**Rationale**: A conformance-check finding surfaced that Layer 3 documentation (`mode-drift/layer-3-mode-confirmation.md`) lists `peer_reviewer_pool_underflow` as a valid `escalation_type` emitted to the reporter API, but the v1.0 enum did not include it. A deployer's Reporter implementing Layer 3's documented escalation surface would have been rejected at the API with `400 unknown_escalation_type`. Synthetic Charter 5 (`peer-reviewer-pool-underflow`) in the test apparatus is designed to exercise this exact path. Extending the enum is cleaner than rerouting through `charter_escalation_rule_invoked` or `schedule_of_records_exception`, both of which would have required ad-hoc narrative on every pool-underflow event.

**Scope**: This amendment touches the wire contract (`escalation_type` enum). Per the v1.0 spec's "Items NOT preserved (locked): everything in §§1-6 above" rule, any deviation from §6 requires a contract amendment under steward review. The amendment is additive (no value removed; one value added), so existing v1.0 Reporter implementations remain valid against v1.1. The signal `peer_reviewer_pool_underflow` is already specified by Layer 3's peer-reviewer designation rule (sub-rule 4: pool minimum 3); the wire contract was the only place the value was missing. The amendment closes a documented inconsistency between the Layer 3 prose and the OpenAPI binding while preserving the 1:1 mapping between Layer 3 documented escalation events and reporter API enum values.

**OpenAPI binding updated**: `reporter-api.openapi.yaml` `info.version` 1.0.0 → 1.1.0; enum extended to 9 values.

**Locked at v1.1.0 for the v1.0 reference-files release.**

### v1.2.0

**Change**: Added `every_mode_2_record_carries_disclosure_pointer` to the `evidence_metric` enum (now 24 values, previously 23), with the signal list.

**Rationale**: The text lists the signal at Level 2 (Standard §7.3.2). It reports, for an existing Level 2 criterion, the disclosure pointer the text already required from `drafted` (Standard §4.3, §6.2.2). The value was added to the enum with the signal, before this version number was raised; raising it here keeps one version number from naming two different enums.

**Scope**: additive (no value removed; one value added), so existing v1.1 Reporter implementations remain valid against v1.2.

**OpenAPI binding updated**: `reporter-api.openapi.yaml` `info.version` 1.1.0 → 1.2.0; `evidence_metric` enum extended to 24 values.

**Released with reference files 5.2.0**, together with the field-pair amendment below, which leaves the OpenAPI file unchanged.

### Additive amendment (the field-pair rule)

**Change**: Section 6 points to `reporter-api.openapi.yaml` instead of carrying a copy of the request schema. The copy had drifted from the OpenAPI file: its `evidence_metric` list carried `soft_flag_rate_breach`, which is not a signal and was never in the OpenAPI enum, and it lacked eight signals the OpenAPI enum carries. The field-pair rule now names only pairs whose two values exist in the OpenAPI enums, and the response example echoes a real signal.

**Scope**: additive. No value is removed from the binding contract. A request with `escalation_type: layer_1_soft_flag_rate_breach`, which the old pair example could never match with a listed signal and so returned `422`, is now accepted with any listed signal. This change leaves `reporter-api.openapi.yaml` unchanged, byte for byte.
