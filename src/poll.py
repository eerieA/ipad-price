"""Fetch sources, keep the raw bytes, append one observation per listing
(plan.md §4, §5).

    python src/poll.py --sources apple_refurb apple_new

A source that fails — blocked, challenged, changed layout, or zero listings —
is reported and skipped; the others still run (§8). The exit status is 1 if
any source failed, so a scheduler can see it.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

from sources import apple

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OBSERVATIONS = ROOT / "data" / "observations"

EXTRACTORS = {
    "apple_refurb": apple.refurb_records,
    "apple_new": apple.new_records,
}

# The identity scripts/probe.py placed every source with (plan §3).
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


class SourceFailed(Exception):
    pass


def load_sources():
    data = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    return {source["id"]: source for source in data["sources"]}


def new_session(client):
    if client != "requests":
        raise SourceFailed(f"client {client!r} is not implemented yet")
    session = requests.Session()
    session.headers["User-Agent"] = BROWSER_UA
    return session


def fetch(source, stamp):
    """[(url, body)] for every step, fetched in one session. Each response is
    saved to data/raw before it is judged, blocked pages included."""
    session = new_session(source["client"])
    pages = []
    for number, step in enumerate(source["steps"], 1):
        response = session.get(step["url"], timeout=30)
        body = response.content
        save_raw(source["id"], stamp, number, body)
        challenges = [m for m in source["challenge"] if m.encode() in body]
        if response.status_code != 200 or challenges or step["expect"].encode() not in body:
            raise SourceFailed(
                f"step {number} ({step['url']}): HTTP {response.status_code}, "
                f"challenge markers {challenges or 'none'}, "
                f"payload marker {'present' if step['expect'].encode() in body else 'missing'}")
        pages.append((step["url"], body))
    return pages


def save_raw(source_id, stamp, step_number, body):
    directory = RAW / source_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stamp}-{step_number}.html").write_bytes(body)


def append_observations(source_id, records, observed_at):
    directory = OBSERVATIONS / source_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{observed_at[:10]}.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps({"observed_at": observed_at, **record}, ensure_ascii=False) + "\n")
    return path


def poll(source, now):
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    pages = fetch(source, now.strftime("%Y%m%dT%H%M%SZ"))
    records = EXTRACTORS[source["id"]](pages)
    if not records:
        raise SourceFailed("0 listings — a layout change, not an empty store (§8)")
    return append_observations(source["id"], records, observed_at), len(records)


def main():
    sources = load_sources()
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", nargs="+", required=True, choices=sorted(EXTRACTORS))
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    failed = False
    for source_id in args.sources:
        try:
            path, count = poll(sources[source_id], now)
            print(f"{source_id}: {count} listings → {path.relative_to(ROOT)}")
        except Exception as error:  # one source's failure never stops the rest (§8)
            failed = True
            print(f"{source_id}: FAILED — {type(error).__name__}: {error}", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
