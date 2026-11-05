# Roadmap: 12 weeks to interview-ready

The plan assumes interviews in one to three months at about 11 hours a week (the Tech Interview Handbook's three-month plan uses the same budget). Dates live in `notebook/config.json`; pattern data (tiers, target counts, start weeks, cues, invariants, canonical problems) lives in `assets/roadmap.json`. The snapshot compares progress with this plan every time it runs. Treat the split below as a starting point to adjust, not a sourced prescription. Spread the hours over five or six days in 25-minute blocks rather than one or two long sittings: spacing, and the sleep between sessions, do part of the learning.

## What the target interviews test

| Target | Typical loop | What to drill |
|---|---|---|
| Indian product companies | Online assessment with 2–3 mediums, 1–2 live DSA rounds, a 60–120 minute machine-coding round, system design from about 2–3 years of experience | Timed unaided DSA; Python machine coding graded on working code, structure, extensibility, validation and tests |
| GCCs and big-tech India offices | Usually the parent company's global loop (Atlassian splits coding into "Data Structures" and "Code Design") | Unaided DSA, code reading and code design |
| Global remote applied-AI roles and AI startups | Often one DSA screen plus RAG or agent take-homes with evals, AI-assisted live coding and applied system design | Plan-first AI-assisted builds, debugging, a maintained DSA floor at about LeetCode medium |

AI-assisted rounds are spreading (Canva since 2025, Meta from late 2025, a Google pilot in 2026) while unaided rounds are getting stricter (Anthropic and Amazon ban AI in live rounds). Practise both modes.

## Phases

| Weeks | Phase | Goal | Rough split of the 11 hours |
|---|---|---|---|
| 1–4 | Foundations | Tier-one patterns to "practicing"; a plan card on every problem; daily cards; first machine-coding kata in week 3 | 60% new problems, 25% reviews and cards, 15% machine coding |
| 5–8 | Expansion | Heaps, backtracking, graphs, tries, intervals, greedy, 1-D DP; timed mocks from week 6 | 45% new, 25% reviews and cards, 15% machine coding, 15% mocks |
| 9–12 | Interview mode | 2-D DP and advanced graphs, machine coding, AI-assisted drills, ML coding, weekly mocks, repair of weak patterns | 30% mixed sets and repair, 25% mocks, 15% each for machine coding, AI drills and ML coding |

## Pattern order (start week)

| Week | Patterns |
|---|---|
| 1 | Arrays & Hashing, Two Pointers |
| 2 | Sliding Window, Prefix Sums, Stack (including monotonic stack) |
| 3 | Binary Search (including search on the answer), Linked List, first machine-coding kata |
| 4 | Trees |
| 5 | Heap / Priority Queue, Backtracking |
| 6 | Graphs, Tries |
| 7 | Intervals, Greedy, 1-D DP |
| 8 | 2-D DP, Advanced Graphs |
| 9 | Math & Geometry, Bit Manipulation, machine coding continues |
| 10 | AI-assisted coding, ML coding |
| 11–12 | Mocks, unlabeled mixed sets, re-solves of anything not yet retained |

Tier one covers what recurs most across interview guides: hashing and counting, two pointers and sliding windows, sorting and intervals, stacks, heaps and top-k, binary search, BFS/DFS, tree recursion and backtracking. Tier two adds tries, union-find, topological sort, Dijkstra, greedy and core DP. Tier three is applied data-structure design plus the AI-engineer-specific rounds.

## Problem lists

- **NeetCode 150** is the spine: 18 sections, each with a solution video. Section sizes are the `target` values in roadmap.json.
- NeetCode 150 barely covers prefix sums and binary search on the answer, so the roadmap adds a Prefix Sums block and Split Array Largest Sum.
- Grind 75 is the fallback if a date gets close; NeetCode 250 only for weak sections; Sean Prashad's LeetCode Patterns list when you need more problems of one pattern.
- Depth on about 100–150 anchor problems re-solved on schedule beats hundreds of one-shot solves: LeetCode volume correlates only modestly with interview performance (r = 0.27), with diminishing returns past about 500 problems.

## Readiness

A pattern is interview-ready when at least three of its problems are "ready" (see references/learner-model.md) and it holds up on unseen problems in mocks. Overall readiness is the average of several observed mocks, not a single good day, because only about 20% of candidates perform consistently across interviews. Add a human mock every two to three weeks from week 6.

## Interleaving

Learn a new pattern in a short block (worked example, faded example, solo problem), then mix it unlabeled with confusable patterns. Blocked practice looks better during practice but lost 20–63% a week later in one study. `coach.py next` does this:
- A pattern's first three problems come together, with the pattern named.
- After that, new problems rotate across the started patterns, least recently practised first, and are presented without the pattern name.
- A new pattern starts when its week arrives.

Useful contrastive pairs:

- Subarray sum equals k with negatives (prefix sums + hash map) vs all positive (sliding window)
- Two Sum on unsorted input (hash map) vs sorted (two pointers)
- BFS shortest path (unweighted) vs Dijkstra (weighted)
- Subsets (backtracking) vs counting subsets (DP)
- Merge intervals (sort by start) vs non-overlapping intervals (sort by end)
