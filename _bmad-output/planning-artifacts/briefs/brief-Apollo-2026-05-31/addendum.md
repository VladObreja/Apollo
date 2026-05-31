# Addendum — Apollo Product Brief

Content captured during briefing that belongs in downstream documents (PRD, architecture, solution design) or earned a place in the record without fitting the brief itself.

---

## Prior Art — Depth Notes

**Russell Targ / SRI team.** Operated in the early 1980s. Applied RV to silver futures. Reported moderate success. No systematic data infrastructure; human analyst layer throughout. Results were not built upon cumulatively.

**"Sean" / independent practitioners.** Practitioner active in public psi literature; authored works including material on RVing lottery numbers and financial markets. Name unconfirmed at time of briefing. Claimed moderate success. Same infrastructure limitations as SRI work.

Working hypothesis on the public record: both authors likely represent floor estimates. The zero-sum nature of market alpha means that any practitioner with a genuine edge has a structural incentive to publish nothing. The public record is a biased sample.

**Radin, D. (2026).** Most recent book cited as a well-documented reference for the existing corpus of rigorous psi studies. Title unconfirmed at time of briefing — verify before citing in downstream documents.

---

## ARV — Integration Pathway Notes

Associative Remote Viewing (ARV) is a formal protocol variant in which binary outcomes are associated with two distinct sensory target images rather than asked as direct questions. The rationale is that RV works more reliably on concrete sensory targets than abstract binary propositions.

The v1 target-question formulation approach is structurally adjacent to ARV and may be characterised as a soft variant. The architecture is designed to be compatible with formal ARV integration.

Deferred from v1 because: the asset is not versed in the ARV protocol, and the incremental complexity is not warranted until v1 baseline data exists.

---

## Motivation-Psi Interaction

The asset participates on equal financial terms. This introduces a candidate confounding variable: motivated participants may perform differently from disinterested ones in ways that are attributable to motivation rather than to protocol variables.

The system should be designed to capture motivation state as a session metadata field (distinct from self-assessed session quality) so that this interaction can be studied as the dataset matures.

---

## Non-Financial Target Validation Challenge

Non-financial targets (e.g., historical factual questions without a living record) present a separate epistemological problem: the ground truth may be unavailable, contested, or unknowable. These targets are included for protocol health and asset engagement, not as tradeable signals.

The system should flag non-financial targets as unvalidatable at intake and exclude them from signal extraction. Their session data may still be useful for studying session quality correlates.

---

## Statistical Methodology — Open Questions for PRD

- What sample size is required to achieve statistical significance at a given confidence level for hit rate above chance? Needs a statistician or simulation.
- How is "hit" defined for a financial target? Direction only? Magnitude threshold? Both?
- How are sessions with partial or ambiguous outputs handled in the statistical model — excluded, downweighted, or treated as a separate category?
- How are epistemological epoch transitions applied retroactively to historical data without introducing reanalysis bias? Needs a formal protocol.
- What is the minimum number of sessions before signal extraction is attempted? Running significance testing on small samples inflates false positive rate.

---

## Asset Capacity Constraint

Asset capacity is assumed to be scarce. This is a throughput constraint: the number of sessions per week is bounded by the asset's availability and energy, not by the system's processing capacity. Protocol design should not assume high-frequency session delivery. Target corpus size and session cadence should be calibrated to what the asset can sustain without degrading session quality.

---

## Front-Loaded Protocol — Deferred Study Axis

Determining whether explicitly front-loaded questions ("will asset X move up or down by Friday?") can be answered reliably is itself a high-value research output. Deferred from v1 to preserve the double-blind baseline. Should be introduced as a controlled study axis once a baseline signal is established — not before, or the confound cannot be measured.
