"""Fetch sources, keep the raw bytes, append one observation per listing
(plan.md §4, §5).

    python src/poll.py --sources apple_refurb apple_new bestbuy bestbuy_marketplace

A source that fails — blocked, challenged, changed layout, or zero listings —
is reported and skipped; the others still run (§8). The exit status is 1 if
any source failed, so a scheduler can see it.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from itertools import count
from pathlib import Path

import requests
import yaml
from curl_cffi import requests as curl_requests

import specs
from sources import apple, bestbuy

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OBSERVATIONS = ROOT / "data" / "observations"

# source id → records(source, get, catalog). `get(url, expect)` is the one
# way a fetcher touches the network (see `requester`).
EXTRACTORS = {
    "apple_refurb": lambda source, get, catalog: apple.refurb_records(fetch_steps(source, get)),
    "apple_new": lambda source, get, catalog: apple.new_records(fetch_steps(source, get)),
    "bestbuy": bestbuy.records,
    "bestbuy_marketplace": bestbuy.records,
}

# The identity scripts/probe.py placed every source with (plan §3).
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# Politeness between one source's requests (§8). Best Buy makes hundreds.
REQUEST_DELAY_S = 0.5


class SourceFailed(Exception):
    pass


def load_sources():
    data = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    return {source["id"]: source for source in data["sources"]}


def new_session(client):
    if client == "curl_cffi":
        return curl_requests.Session(impersonate="chrome")
    session = requests.Session()
    session.headers["User-Agent"] = BROWSER_UA
    return session


def requester(source, stamp):
    """get(url, expect) → body, over one session for the whole poll, so a
    later request carries the cookies an earlier one earned. Each response is
    saved to data/raw before it is judged, blocked pages included, and any
    failed request fails the source (§8)."""
    session = new_session(source["client"])
    numbers = count(1)

    def get(url, expect):
        number = next(numbers)
        if number > 1:
            time.sleep(REQUEST_DELAY_S)
        response = session.get(url, timeout=30)
        body = response.content
        save_raw(source["id"], stamp, number, body)
        challenges = [m for m in source["challenge"] if m.encode() in body]
        if response.status_code != 200 or challenges or expect.encode() not in body:
            raise SourceFailed(
                f"request {number} ({url}): HTTP {response.status_code}, "
                f"challenge markers {challenges or 'none'}, "
                f"payload marker {'present' if expect.encode() in body else 'missing'}")
        return body
    return get


def fetch_steps(source, get):
    """[(url, body)] for a source whose `steps` are fixed URLs."""
    return [(step["url"], get(step["url"], step["expect"])) for step in source["steps"]]


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


def poll(source, now, catalog):
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    get = requester(source, now.strftime("%Y%m%dT%H%M%SZ"))
    records = EXTRACTORS[source["id"]](source, get, catalog)
    if not records:
        raise SourceFailed("0 listings — a layout change, not an empty store (§8)")
    return append_observations(source["id"], records, observed_at), len(records)


def main():
    sources = load_sources()
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", nargs="+", required=True, choices=sorted(EXTRACTORS))
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    catalog = specs.load_catalog(ROOT / "config" / "models.yaml")
    failed = False
    for source_id in args.sources:
        try:
            path, listings = poll(sources[source_id], now, catalog)
            print(f"{source_id}: {listings} listings → {path.relative_to(ROOT)}")
        except Exception as error:  # one source's failure never stops the rest (§8)
            failed = True
            print(f"{source_id}: FAILED — {type(error).__name__}: {error}", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
