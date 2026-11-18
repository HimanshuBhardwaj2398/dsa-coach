# Binary Search

Pattern: binary-search · Created: 2026-11-16

## Core idea

(One paragraph in your own words: what the pattern does and why it is correct.)

## Plan card

(Fill in from assets/templates/plan-card.md for the canonical problem.)

## Invariant

## Explainers

(Saved pages are listed in artifacts/registry.json and in JOURNEY.md.)

## Questions asked

- 2026-11-18 (q0008): How do I choose < vs <= in the loop and where equality goes in the comparisons, across plain binary search and rotated arrays (find minimum, find target)? Wants a basic template and what changes per case.
- 2026-11-17 (q0007): Rotated search: when we say left and right half, is mid in both?

## Changelog

- 2026-11-18 (v3, q0008): Added "Choose the loop": four questions that set the guard, start and updates; pairs that must go together; three templates (found on the spot, first that passes, last that passes); the family table; where each = comes from in rotated search, with LC 153 behind a spoiler; a loop lab whose 480 variants were all run in Python by variants.py; "Where it breaks"; and a guard question in the hidden check.

- 2026-11-16 (v2, q0006): Broadened the explainer with recognition questions, monotone predicates and candidate spaces, a verified minimum-speed trace on unsorted jobs, limits and related variants, and hidden transfer checks. Preserved the original array walkthrough.

- 2026-11-16: created
