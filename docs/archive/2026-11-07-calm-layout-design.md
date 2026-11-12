> **Archived.** Built in 0.5.2; the Solve tab was removed in 0.9.0. Kept for history: paths inside are as they were when it was written.

# Study app: a calmer Solve tab

Date: 2026-11-07 · Status: approved in brainstorming · Target: dsa-coach 0.5.2 · Builds on `2026-11-06-study-app-solve-design.md`

## Goal

The Solve tab shows everything at once: the whole attempt file, every label, the file path and the due line. Himanshu likes how practice sites hide what he doesn't need right now. This change gives the page a calmer layout using the same principles. It doesn't copy any site's branding, colours or styling. **Only the page changes**: the server, the API, the files and every behaviour stay as they are.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Layout | Two panes. Tabs on the left; editor over a collapsible test console on the right | Familiar from practice sites; the statement stays one click away while coding |
| Plan card, EXAMPLES and run block in the editor | Folded on load into one-line markers, one click to open; still in the file | The file stays honest: the coach and `python3 file.py` see what he sees; no second copy to keep in step |
| Theme | One calm theme in light and dark, following the system setting | Less visual noise; dark is what he's used to on practice sites |

## Layout

- **Top bar:**
  - The problem title links to LeetCode, and the file path shows on hover.
  - Eight small stage dots sit next to "Stage N · name". The dots are clickable and keep today's rules: jumping ahead asks "Which stage are you in?", and unsaved stage text is saved first.
  - The timer is small and muted.
  - The hint rung appears only once a hint has been used.
  - On the right are **Run** and **Ask coach**. Unsaved code shows as a dot on Run.
- **Left pane, three tabs:**
  - **Description:** the statement, fetched or pasted. It is re-read from disk each time the tab opens, so a statement written elsewhere shows up. When there's no statement, it holds the fetch/paste flow from 0.5.1.
  - **Stage:** only the current stage's question, its box or boxes, and Done / Save. Stage 1 keeps the restatement and the examples table, stage 6 the plan-card fields, and stage 8 the look-back boxes plus Finish. Park stays where it is today, in the block-over banner.
  - **Notes:** the saved answers from earlier stages, read-only, one per stage. Clicking one opens that stage in the Stage tab.
  - The tab opens on **Stage**. On a solve's first load with no statement, it opens on **Description**.
- **Right pane:**
  - **Editor:** CodeMirror. On load it folds the module docstring (marker `▸ Plan card`), the `EXAMPLES` block with its comment lines (`▸ EXAMPLES (n)`) and the `if __name__ == "__main__":` block (`▸ run block`). A fold that's open stays open across saves and polls. The textarea fallback shows the whole file, as now.
  - **Console:** two tabs below the editor; a header button collapses it to one line.
    - **Testcases:** one chip per EXAMPLES row, with edge rows marked. A chip shows its input and the expected output. The rows are still edited in stage 1's table or in the editor.
    - **Result:** after Run, a pass/fail chip per case. Selecting one shows its input, output, expected value and stdout, and the error if it failed. The run's top-level error (a timeout or a crash naming the example) goes above the chips. Run switches to this tab.
- **Start screen:** a centred card with the next pick, the slug, the difficulty and the confidence. "Pattern" and the due line sit under **More options**.
- **Banners** (errors, rescue, conflict, block over, finish) stay as they are, restyled.

## Unchanged

Every API call, the `change()` queue, polling every 3 s, the conflict and rescue flows, Ask the coach and the finish prompt, Park, `beforeunload`, keyboard shortcuts, SRI on the CDN tags, `server.py`, `runner.py`, `attempt_file.py` and coach.py.

## Testing

- **Headless Chromium:** the existing check (`check.py`, 44 steps) is updated for the new selectors. Every behaviour it covers must still pass. New checks:
  - the folds on load, and that they survive a save;
  - Run switches to Result with a chip per case, and the console collapses;
  - opening the Description tab re-reads the statement;
  - clicking a Notes entry opens that stage;
  - the start screen's More options.
- **Screenshots** at 1440×900, in light and dark.
- `node --check`, and both test suites, which are unchanged.

## Out of scope

A draggable pane divider, keyboard shortcuts for the tabs, and any change to the server or the files.
