# Content pipeline — @nftepml ("Crypto Heathen")

Build-in-public backtest lab. Every post is artifact-backed and verdict-labeled.

## Rules (non-negotiable)
- Numbers only from `results/runs/<run_id>.json`; every post cites its `run_id`.
- `python code/vrun.py guard --report content/posts/<file>.md` must pass before pasting.
- Killed strategies are posted as "tested and failed" — never as edges.
- CANDIDATEs are labeled unproven. Not financial advice.
- `run_id` is never repeated (see `posted.jsonl`).

## Post format (2 tweets, 280 chars each)
- **Tweet 1 — hook:** a concrete, surprising number, `$PAIR`, emoji, and the
  tension of the story. The verdict is *not* announced here.
- **Tweet 2 — payoff:** stats, explicit verdict + reason, funding caveat, repo
  link, hashtags, `NFA`.

One file = one post. One block = one tweet. Never split a block.

## Layout
- `posts/` — generated, paste-ready posts (one blank line between tweets)
- `WEEK.md` — complete copy-paste text of every post in the pack
- `SCHEDULE.md` — UTC calendar (01:30 / 13:00 / 21:00 UTC)
- `manifest.jsonl` — one line per post (file, UTC time, slot, run_id, verdict)
- `posted.jsonl` — append-only ledger of what actually went out
- `x_queue.py` — generator (`build`, `verify`)

## Workflow (X Web Scheduler, option 2)
1. Generate/refresh: `python code/x_queue.py build --days 30`
   Optional: `--start 2026-11-09` (UTC date). Slots already in the past are
   always skipped, so a rebuild never produces a post with a past timestamp.
2. Gate: `python code/x_queue.py verify` (guard on every file; must be 90/90)
3. Open `content/WEEK.md` or `content/posts/`, copy tweet 1, then tweet 2,
   and schedule each with X's calendar icon.
4. After scheduling, append the file + run_id to `posted.jsonl`.

## Honest labels
KILLED ≠ bad content — it's the lab showing its work. What never ships:
unbacked numbers, unverified claims, CANDIDATEs sold as alpha.
