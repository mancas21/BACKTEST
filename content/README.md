# Content pipeline — @nftepml ("Crypto Heathen")

Build-in-public backtest lab. Every post is artifact-backed and verdict-labeled.

## Rules (non-negotiable)
- Numbers only from `results/runs/<run_id>.json`; every post cites its `run_id`.
- `python code/vrun.py guard content/posts/<file>.md` must pass before pasting.
- Killed strategies are posted as "tested and failed" — never as edges.
- CANDIDATEs are labeled unproven. Not financial advice.
- `run_id` is never repeated (see `posted.jsonl`).

## Layout
- `posts/` — generated, paste-ready threads (one block = one tweet)
- `SCHEDULE.md` — UTC calendar for the pack (01:30 / 13:00 / 21:00 UTC)
- `manifest.jsonl` — one line per post (file, UTC time, slot, run_id, verdict)
- `posted.jsonl` — append-only ledger of what actually went out (mark manually or via script)
- `x_queue.py` — generator (`python code/x_queue.py build|verify`)

## Workflow (X Web Scheduler, option 2)
1. Generate/refresh: `python code/x_queue.py build --days 30`
2. Gate: `python code/x_queue.py verify` (guard on every file)
3. You open x.com, paste each thread per `SCHEDULE.md`, hit the Schedule icon
4. After posting, add the URL to `posted.jsonl` (one line: file, run_id, posted_utc)

## Honest labels
KILLED ≠ bad content — it's the lab showing its work. What never ships:
unbacked numbers, unverified claims, CANDIDATEs sold as alpha.
