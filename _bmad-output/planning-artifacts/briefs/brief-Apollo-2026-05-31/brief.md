---
title: Apollo — Product Brief
status: draft
created: 2026-05-31
updated: 2026-05-31
polished: 2026-05-31
---

# Product Brief: Apollo

## Executive Summary

Apollo is a personal AI-augmented research system for applying Remote Viewing (RV) to financial market prediction. It treats psi effects as axiomatic — grounded in a substantial peer-reviewed literature — and investigates whether a structured, AI-mediated protocol can reliably channel those effects into actionable trading signals.

The system manages the full pipeline: target selection, session delivery, response capture, ground-truth validation, and statistical analysis, with a continuous feedback loop in which the human administrator and AI agent together refine the epistemological framework over time. The first iteration focuses on financial markets both as a tractable study domain and as a potential source of revenue.

The deeper ambition is to develop a rigorous, instrumented understanding of psi functioning — what conditions enable it, what conditions degrade it, and what can be reliably extracted from it given the current protocol. Revenue is a byproduct of that understanding, not the primary objective.

## The Problem

Prior attempts to apply RV to financial markets — Russell Targ's SRI team in the early 1980s and subsequent independent practitioners — operated without systematic data infrastructure. Session outputs were captured manually, interpretive analysis was performed by human analysts (introducing both bottlenecks and bias), and no mechanism existed for retroactively applying updated interpretive frameworks to historical data. Each study was epistemically isolated: methodology was difficult to compare across studies, and no feedback loop existed between research outcomes and protocol refinement.

The public record of this work trends toward "moderate success." This is likely a floor estimate. Market alpha is zero-sum: any practitioner with a genuine edge has a strong structural incentive to publish nothing. Absence of strong public claims is not evidence of absence of strong private results. The silence is what the incentive structure predicts.

The gap is not evidence that the approach doesn't work. The gap is infrastructure: no known prior attempt had the tools to build a systematic, cumulative, self-correcting research instrument around the problem. The missing piece was an AI interpretation layer. Without it, any email-based protocol requires a human analyst at every session — expensive, slow, bias-prone, and unscalable. Large language models make the Apollo architecture viable in a way that was not previously accessible.

## The Solution

Apollo replaces the human analyst layer with an AI agent while preserving human judgment at the administrative and epistemological level.

**Target selection.** The administrator and AI agent collaboratively curate a corpus of financial targets filtered on volatility, liquidity, and accessibility. Classical technical signals may be incorporated as an additional filter in later iterations.

**Session delivery.** The system extracts targets and delivers them via email to the asset. Target framing is configurable from fully double-blind to explicitly front-loaded. The v1 default is double-blind, consistent with the Western RV literature's insistence on this condition as a validity control.

**Session capture.** The asset performs the RV session and replies via email with their impressions. The reply also captures structured metadata — sleep quality, social context at the time of session, self-assessed confidence in the quality of the act itself, and other session variables — some of which are captured automatically by the system. This metadata is research data, not administrative overhead.

**Interpretation and validation.** The LLM agent reads the reply, interprets freeform session output, validates completeness, writes structured records to the database, and follows up with the asset if clarification is needed.

**Ground-truth validation.** At prediction timeline expiry, each session is validated against actual market outcomes and the result is encoded.

**Signal extraction.** As sessions accumulate, statistical analysis produces a confidence-weighted signal representing the system's current degree of trust in its measurements. This signal can operate as a standalone trading input or be integrated as a weighted component of a classical strategy.

**Epistemological review.** The administrator and agent collaborate continuously on the accumulated data, refine the interpretive framework, and record each substantive update as an epistemological epoch transition. Epoch changes can be applied retroactively to historical raw data without corrupting the underlying record.

## What Makes This Different

**AI-mediated session processing.** The email interface is deliberately low-tech: asynchronous, timestamped, format-agnostic, and zero cognitive overhead for the asset at the moment of session. The AI layer handles everything downstream — interpretation, validation, structured extraction, follow-up — without introducing human analyst bias or throughput limits.

**Epistemological epoch tracking.** Apollo version-controls its interpretive framework. As understanding of the system's psi functioning develops, the framework can be updated and applied retroactively to historical raw data. This is not methodological drift — it is principled reanalysis. Most research systems don't build this in from the start.

**Systematic metadata capture.** Session variables beyond the RV output itself — automatically captured and reported alongside each measurement — are candidate correlates of psi performance. Over time, the dataset may reveal what conditions reliably enable or degrade the asset's accuracy: a research output independent of any trading result.

## Who This Serves

**Administrator.** Manages target corpus selection, reviews agent interpretations, sets and revises the epistemological framework, and makes trading decisions informed by the extracted signal. Also the primary research beneficiary: Apollo is an instrument for understanding psi functioning, and the administrator is both operator and investigator.

**The asset.** Performs RV sessions via email, receives structured feedback on their performance over time as the dataset matures, and participates equally in any financial outcomes — an ethical position with a research dimension: motivated participants may perform differently from disinterested ones, and the system is designed to surface the effect if it manifests. The design minimizes operational burden: one email received, one email sent. The protocol imposes as little on them as possible so that session quality is the only variable they need to attend to.

## Success Criteria

**Trading signal.** A hit rate above chance at a confidence level sufficient to support positive expected value as a market strategy. The precise threshold is to be empirically determined — the system is designed to discover this number, not assume it.

**Research signal.** Measurable insight into at least one psi correlate — sleep quality, social context, self-assessed session quality, or motivation — over the course of v1 data accumulation.

**Operational signal.** The pipeline runs without manual intervention at the session capture and interpretation layer.

**Null result handling.** Psi existence is treated as axiomatic. If statistical analysis over a meaningful accumulation of sessions yields no signal distinguishable from noise, the conclusion is that this arrangement is insufficient — not that the underlying phenomenon is absent. Something about the protocol is wrong, and the data shows where to look. Protocol revision follows.

## Scope

**In for v1:**
- Single asset
- Financial market targets as primary domain
- Non-financial targets included in small quantity as protocol health and asset engagement measures — results are not tradeable and validation may not be achievable
- Double-blind target framing as default
- Prediction horizon: hours to days preferred; weeks possible but constrained by asset capacity
- Email-based session delivery and capture
- LLM-mediated interpretation, validation, and database write
- Agent-initiated follow-up for incomplete or ambiguous sessions
- Ground-truth validation at timeline expiry
- Statistical analysis for signal extraction
- Epistemological epoch tracking from day one

**Explicitly out for v1:**
- Automated trade execution — signal informs human decision; execution is manual
- Multiple assets
- Associative Remote Viewing (ARV) as a formal protocol — the architecture is compatible; integration is deferred, not excluded
- Front-loaded target framing as a controlled study axis — deferred to later iteration
- Classical signal integration as a corpus filter — deferred; incorporation is possible ad hoc

## Vision

If v1 produces a statistically meaningful signal, Apollo becomes a platform for systematic psi research with financial markets as the primary validation domain. The protocol expands to accommodate multiple assets, enabling cross-asset comparison and signal aggregation. Front-loaded target framing is introduced as a controlled study axis — determining whether and how explicitly stated questions can be answered reliably is itself a high-value research output. ARV is integrated as an optional protocol variant. Classical trading signals are woven into corpus selection and potentially into signal weighting.

The epistemological framework matures from a working hypothesis about confidence into a more granular model of what conditions produce reliable psi performance — what the asset can do, under what circumstances, at what time horizons, and with what reliability. The system becomes an instrument for understanding the structure of psi functioning. Revenue, if it comes, is evidence that the instrument works.
