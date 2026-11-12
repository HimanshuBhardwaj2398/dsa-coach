> **Archived.** Built in 0.5.1; the statement fetcher was removed in 0.9.0. Kept for history: paths inside are as they were when it was written.

# Study app: fetch the problem statement

Date: 2026-11-07 · Status: approved, built · Target: dsa-coach 0.5.1 · Builds on `2026-11-06-study-app-solve-design.md`

## Goal

Himanshu shouldn't have to paste a LeetCode statement into the Solve tab. When a solve starts and the problem has no `problem.md`, the app fetches that one statement from LeetCode and saves it. Pasting stays as the fallback.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Preload all ~150, or fetch one at a time | One at a time, when a solve without a statement opens | LeetCode has no official API. One request per problem at human pace is ordinary use; a bulk pull looks like scraping and is likelier to be blocked |
| Source | `https://leetcode.com/graphql`, the endpoint LeetCode's own site uses: `question(titleSlug)` → `title`, `content` (HTML), `isPaidOnly` | The only source of the exact statement; no login needed for free problems |
| When it fails (offline, endpoint changed, premium problem, empty content) | The page shows the paste box as today, with one line saying why the fetch failed and a **Fetch from LeetCode** button to retry | Pasting always works |
| Format saved | Plain text: `# <title>`, the link, then the statement with HTML turned into text (paragraphs, lists as `- `, `<pre>` blocks kept, `<sup>` as `^`, entities decoded) | `problem.md` is read by him in the panel and by the coach in the chat; HTML would be noise for both |
| Git | `notebook/problems/*/problem.md` is in `.gitignore`, fetched or pasted | The repo is public; statements are LeetCode's text and shouldn't be republished |

## Design

- **`app/statement.py`** (new, stdlib only):
  - `fetch(slug, opener=urllib.request.urlopen, timeout=10) -> (title, html)`. It posts one GraphQL query, with a generic User-Agent and a Referer of the problem's page. It raises `StatementError` with a short reason when the problem is premium, the content is empty, or the network or JSON fails.
  - `to_text(html) -> str`, built on `html.parser`.
  - `opener` is injectable, so tests never touch the network.
- **`app/server.py`**: a new route, `POST /api/problem/fetch {slug}`.
  - If `problem.md` already exists, it returns it without fetching.
  - Otherwise it calls `statement.fetch`, writes `problem.md` (the same atomic write as `put_problem`) and returns `{"text": ...}`.
  - On `StatementError` it returns a 502 `{"error": "Couldn't fetch the statement: <reason>. Paste it instead."}`.
  - The slug passes `check_slug`. The host is fixed, never taken from the request.
- **The page**:
  - When a solve's first load finds no statement, it calls the fetch route once for that solve.
  - While the fetch runs, the statement box says "Fetching the statement from LeetCode…".
  - On success the statement shows as if it had been pasted. On failure, the paste box appears with the reason and a **Fetch from LeetCode** retry button.
  - Polling never triggers a fetch.
- **Docs**: the CHANGELOG (0.5.1), platforms.md's study-app paragraph, and this spec's predecessor (the "Problem statement" decision row and stage 1, step 2).

## Testing

- `tests/test_statement.py`:
  - `to_text` on a fixture shaped like LeetCode's HTML (paragraphs, `<pre>` examples, `<ul>` constraints, `<sup>`, `&lt;`).
  - `fetch` with a fake opener: success, premium, null content, bad JSON and a network error.
- `tests/test_server.py`:
  - The fetch route writes `problem.md` and returns it.
  - It returns the existing file without calling the opener.
  - A 502 with the reason, with nothing written.
  - The server gets its opener through a module attribute the test can replace.
- **Live check:** one real fetch of `koko-eating-bananas`, from the running app, when he starts that solve.

## Out of scope

Premium problems (they would need his LeetCode login), bulk preloading, and other sites.
