# AlphaBrain public plan record — independent daily snapshots

This repository is written by a scheduled GitHub Actions job, not by the AlphaBrain
server. Once a day it fetches the public plan record from
`https://alphabrain-ai.com/record` (the same JSON the page renders), recomputes the
cohort's manifest hash, and commits:

- `manifests/YYYY-MM-DD.json` — the day's manifest: the served hash, the recomputed
  hash, every matured plan's id / symbol / state, the full public corrections list, and
  the evaluator version and code hash taken from a replay bundle;
- `ledger/YYYY-MM-DD.json` — the complete public ledger as served;
- `MANIFESTS.md` — one line per day, newest first.

Why this exists: a record that its operator can edit silently is not a record. The
site prints a manifest hash and lists every correction; this repository keeps the
history of both on infrastructure the operator does not control. The commit time is
GitHub's clock. Rewriting a past day here would need a force-push, which is visible.

How to check a claim:

1. Open `manifests/<date>.json` and compare `manifest_sha256_served` with what the
   site printed on that day (or with `manifest_sha256_recomputed`).
2. If two days' manifests differ, the difference must be explained by new matured
   plans (published ≤ 35 days earlier, window rolling) or by an entry in
   `corrections`. A change with neither is a question to put to the operator.
3. Any plan can be replayed offline: download its bundle (`replay_url` in the
   ledger) and run `replay_bundle.py` from the AlphaBrain repository. The bundle
   carries the candles, their hash and the evaluator code hash.

What this is not: a performance claim. States are barrier touches on 5-minute candles
of a model scenario, stop first when both print in one candle, no fees, no fills, no
P&L. Read the methodology page before drawing a conclusion from a count.
