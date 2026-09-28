# Layer 1 — Statistical Detection (Scaffolding-Only in v5.0)

**Authority**: Mode-Drift mitigation Layer 1
**Status**: First release ships **detection-only scaffolding**. Enforcement gates phase in at implementation-lifecycle Week 7+.

---

## What Layer 1 Does

An independent Mode-2-trained classifier samples Mode-1-declared closed decision records, re-classifies against substantive-content features (not metadata), and routes drift candidates above threshold to Layer 3.

## Sampling Configuration

| Charter type | Baseline rate | Override |
|---|---|---|
| Standard Mode-1 Charters | 15% stratified | First-100-records-per-Charter rule overrides to 100% until 100 closed records exist |
| `mode-1-with-embedded-mode-2-summary` Charters | 30% stratified | Same first-100 override |

The 15% baseline threads the needle: below it, drift-rate confidence intervals at the Charter level are too wide to be useful; above 30% the human-review queue load saturates available reviewer capacity.

## Three-Corpus Training Design

**Each corpus is disjoint from any AI worker output that would later be classified.**

| Corpus | Source | Authoring window | Status in v5.0 |
|---|---|---|---|
| **Layer A** — Authoritative Mode 2 records | Peer-reviewed Mode-2 decision records assembled by the implementer | Implementation lifecycle Weeks 1-3 | Assembled by the implementer |
| **Layer B** — Synthetic Mode 2 examples | Hand-authored from Section 4 worked examples + Charter primer documents | implementation-lifecycle Weeks 1-3 | Assembled by the implementer |
| **Layer C** — Adversarial negative examples | Mode-1 records with deliberately injected Mode-2 substantive content | **implementation-lifecycle Weeks 4-6** | Authored by the implementer |

The classifier training pipeline emits `corpus_id` + `corpus_version` provenance fields. The classifier outputs `classifier_version` + `corpus_version` on every flag so a downstream auditor can verify training-set independence at any point.

## Drift-Flagging Threshold

| Confidence | Action |
|---|---|
| ≥ 0.75 | **Hard flag** — routes to Layer 3 (in enforcement mode) or surfaces in conformance reporter (in detection-only mode) |
| 0.50 - 0.75 | **Soft flag** — surfaces in per-Charter drift-rate aggregate; does NOT interrupt record lifecycle |

If a Charter's soft-flag rate exceeds 5% over a rolling 30-day window, the reporter emits a Charter-level escalation independent of any single record's hard flag (`escalation_type: layer_1_soft_flag_rate_breach`).

## Phased Deployment

| Deployment phase | Lifecycle Window | Activity | Layer 1 mode |
|---|---|---|---|
| Phase 1 | Weeks 1-3 | Layer A + B corpus assembly; classifier trained on A+B; validation against held-out Layer A subset | **Detection-only** |
| Phase 2 | Weeks 4-6 | Layer C adversarial-corpus authoring; classifier retrained on full A+B+C corpus; validation against held-out adversarial subset | **Detection-only** continues |
| Phase 3 | Week 7+ | Enforcement-mode activation | **Enforcement** — hard flags trigger Layer 3 peer-review interrupt |

**"Weeks" refers to implementation-lifecycle weeks measured from first release.** Layer 1 phased deployment runs on its own multi-week cadence; enforcement activation at Week 7+ falls 7 weeks after first release.

## Silent-Drift Closure Note

The mode-drift mitigation closes the silent Mode 1 → Mode 2 drift failure mode at first use because **Layers 2, 3, and 4 fire at first use**. Layer 1's Phase 1-2 detection-only mode means the `no_silent_mode_drift_in_sample` Level 2 signal emits in a known-conservative posture during Weeks 1-6 (false-negatives possible due to incomplete Layer C corpus). The composition closes the drift failure mode; Layer 1's full firing authority arrives at Week 7+ and adds population-level signal — it does not gate that closure.

## Corpus-Authoring Schedule

Layer C adversarial-corpus authoring is scheduled for implementation-lifecycle Weeks 4-6. Quality bar: precision ≥ 0.85, recall ≥ 0.75 against the held-out adversarial subset before enforcement mode activation.

---

*Layer 1 ships scaffolding only at first release. Enforcement deferred to Week 7+. Silent-drift closure preserved by Layers 2/3/4 firing at first use.*
