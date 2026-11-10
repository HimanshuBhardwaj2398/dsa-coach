# Product

## Register

product

## Users

Himanshu, one learner preparing for coding interviews over a 90-day plan. He solves on LeetCode and talks to the coach in Claude Code. The learning app (`python3 app/server.py`) sits beside both: in a browser tab, or in the Chrome side panel next to LeetCode. Sessions run from a single focus block to an evening.

## Product Purpose

A quiet place to see where he is and to study theory: today's solve and what's due, the pattern map, and each pattern's Learn page with its saved explainer. Success means he can glance at his progress and the theory he needs without leaving LeetCode, and the page never disagrees with the notebook (it only reads it).

## Brand Personality

Plain, precise, unhurried. A reference page he reads, not a dashboard competing for attention. Status is present but muted; the theory is the content.

## Anti-references

- Busy practice sites: ads, sidebars, badges, every panel competing for attention.
- Generic SaaS: cards on cards, gradients, hero metrics.
- Copying any practice site's branding, colours or styling.
- A second editor or chat: solving happens on LeetCode, and coaching happens in the chat.

## Design Principles

1. **Show what this moment needs.** Today first; the map and theory one click away.
2. **Read-only.** The page shows the notebook; `coach.py` is the only writer.
3. **Fits a side panel.** Every view works at 320 px without sideways scrolling.
4. **The coach judges.** The page hands the coach prompts; it does not grade or log.

## Accessibility & Inclusion

WCAG 2.2 AA contrast in both light and dark themes (the theme follows the system setting). Everything works by keyboard with visible focus. Respect `prefers-reduced-motion`. Status is never shown by colour alone (text too).
