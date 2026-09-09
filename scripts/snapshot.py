"""Daily snapshot of the AlphaBrain public plan record.

Fetches the public record (funnel + ledger + cohort manifest hash), the public
corrections list and one replay bundle's evaluator identity, then writes:

    manifests/YYYY-MM-DD.json   compact: as_of, manifest hash, counts, corrections, evaluator
    ledger/YYYY-MM-DD.json      the full public ledger as served that day
    latest.json                 the most recent manifest
    MANIFESTS.md                one line per day, newest first

Runs on GitHub's infrastructure, so the commit time and history are not under the
site operator's control. Standard library only.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request

BASE = os.environ.get(
    "ALPHABRAIN_BASE", "https://alphabrain-ai.com/api/data/premium/public"
)
WINDOW_DAYS = int(os.environ.get("ALPHABRAIN_WINDOW_DAYS", "365"))


def get(path: str):
    req = urllib.request.Request(
        f"{BASE}{path}", headers={"User-Agent": "alphabrain-record-snapshot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main() -> int:
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    record = get(f"/outcome-record?days={WINDOW_DAYS}")
    corrections = get("/outcome-corrections?limit=1000")
    ledger = record["ledger"]
    evaluator = None
    for plan in ledger["plans"]:
        if plan.get("archive"):
            try:
                bundle = get(plan["replay_url"].replace("/api/premium/public", ""))
                evaluator = bundle.get("evaluator")
                break
            except Exception:  # noqa: BLE001 - the manifest is still useful without it
                continue
    ledger_sha = hashlib.sha256(canonical(ledger["plans"]).encode("utf-8")).hexdigest()
    manifest = {
        "snapshot_date": today,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": f"{BASE}/outcome-record?days={WINDOW_DAYS}",
        "as_of": record["as_of"],
        "window_days": record["window_days"],
        "manifest_sha256_served": record.get("manifest_sha256"),
        "manifest_sha256_recomputed": ledger_sha,
        "manifest_consistent": record.get("manifest_sha256") == ledger_sha,
        "matured": ledger["matured"],
        "immature": ledger["immature"],
        "no_trade": ledger["no_trade"],
        "headline": record["funnel"]["headline"],
        "by_method": {
            key: {
                k: v
                for k, v in bucket.items()
                if k
                in (
                    "matured",
                    "activated",
                    "not_activated",
                    "activated_outcomes",
                    "not_activated_reasons",
                    "rates_allowed",
                    "tp2_share_min_pct",
                )
            }
            for key, bucket in record["funnel"]["by_method"].items()
        },
        "corrections_count": corrections["count"],
        "corrections_sha256": hashlib.sha256(
            canonical(corrections["corrections"]).encode("utf-8")
        ).hexdigest(),
        "corrections": corrections["corrections"],
        "evaluator": evaluator,
        "plans": [
            {
                "report_id": p["report_id"],
                "plan_index": p["plan_index"],
                "symbol": p["symbol"],
                "method": p["method"],
                "status": p["status"],
                "outcome_class": p["outcome_class"],
                "published_at": p["published_at"],
                "archive": p.get("archive"),
            }
            for p in ledger["plans"]
        ],
    }
    os.makedirs("manifests", exist_ok=True)
    os.makedirs("ledger", exist_ok=True)
    with open(f"manifests/{today}.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
    with open(f"ledger/{today}.json", "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=1, ensure_ascii=False)
    with open("latest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
    line = (
        f"| {today} | `{ledger_sha[:16]}` | {ledger['matured']} | {ledger['immature']} | "
        f"{corrections['count']} | {'yes' if manifest['manifest_consistent'] else 'NO'} |"
    )
    header = (
        "# Daily manifests\n\n"
        "Newest first. `manifest` is the SHA-256 of the canonical public ledger as served that day; "
        "`consistent` says whether the site's own manifest hash matched what this snapshot recomputed.\n\n"
        "| date | manifest | matured | immature | corrections | consistent |\n|---|---|---|---|---|---|\n"
    )
    existing = ""
    if os.path.exists("MANIFESTS.md"):
        existing = open("MANIFESTS.md", encoding="utf-8").read()
    rows = [
        r
        for r in existing.splitlines()
        if r.startswith("| 20") and not r.startswith(f"| {today} ")
    ]
    with open("MANIFESTS.md", "w", encoding="utf-8") as fh:
        fh.write(header + "\n".join([line] + rows) + "\n")
    print(
        json.dumps(
            {
                "date": today,
                "manifest": ledger_sha,
                "consistent": manifest["manifest_consistent"],
                "matured": ledger["matured"],
                "corrections": corrections["count"],
            }
        )
    )
    return 0 if manifest["manifest_consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())
