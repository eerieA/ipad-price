"""Phase 0 reachability probe (plan.md §9).

Runs every source's fetch sequence from config/sources.yaml once per HTTP
client, and prints a markdown report of what came back: status, bytes, which
challenge markers appeared, and whether the real payload did. Run it from
Actions and from the desktop; the reports place each source (§4).

    python scripts/probe.py > probe.md

Only status, sizes and marker names are printed — never response bodies — so
the report is safe to commit to research/.
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from curl_cffi import requests as curl_requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"

# The same Chrome identity curl_cffi presents, so a difference between the two
# clients isolates the TLS fingerprint rather than the User-Agent string.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# Politeness between requests within one sequence (§8).
STEP_DELAY_S = 1.0


def read_yaml(name):
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def new_session(client):
    if client == "requests":
        session = requests.Session()
        session.headers["User-Agent"] = BROWSER_UA
        return session
    return curl_requests.Session(impersonate="chrome")


def placeholder_values(source, watches):
    values = dict(source.get("sample", {}))
    seeds = watches.get(source["id"]) or []
    if seeds:
        values.update({k: v for k, v in seeds[0].items() if k != "note"})
    return values


def run_step(session, url, expect, challenge):
    try:
        response = session.get(url, timeout=30)
    except Exception as error:  # a reset connection is a block like any other
        return {"status": f"ERR {type(error).__name__}", "bytes": 0,
                "challenges": [], "found": False, "ok": False}
    body = response.content
    hits = [marker for marker in challenge if marker.encode() in body]
    found = expect.encode() in body
    return {"status": response.status_code, "bytes": len(body),
            "challenges": hits, "found": found,
            "ok": response.status_code == 200 and not hits and found}


def probe_source(source, client, watches):
    values = placeholder_values(source, watches)
    session = new_session(client)
    results = []
    for index, step in enumerate(source["steps"]):
        if index:
            time.sleep(STEP_DELAY_S)
        results.append(run_step(session, step["url"].format(**values),
                                step["expect"], source["challenge"]))
    return results


def runner_label():
    return "GitHub Actions" if os.environ.get("GITHUB_ACTIONS") == "true" else "desktop"


def main():
    sources = read_yaml("sources.yaml")["sources"]
    watches = read_yaml("watch_urls.yaml")
    clients = ("requests", "curl_cffi")

    detail = []
    summary = []
    for source in sources:
        passed = []
        for client in clients:
            results = probe_source(source, client, watches)
            if all(r["ok"] for r in results):
                passed.append(client)
            for number, r in enumerate(results, 1):
                detail.append(
                    f"| {source['id']} | {number} | {client} | {r['status']} "
                    f"| {r['bytes']:,} | {', '.join(r['challenges']) or '—'} "
                    f"| {'yes' if r['found'] else 'no'} | {'pass' if r['ok'] else 'FAIL'} |")
        summary.append(f"| {source['id']} | {', '.join(passed) or '**none**'} |")

    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Probe — {runner_label()}, {started}",
        "",
        "A source passes on a client when every step of its sequence passes.",
        "",
        "| Source | Passes with |",
        "| --- | --- |",
        *summary,
        "",
        "## Steps",
        "",
        "Step numbers index `steps` in config/sources.yaml.",
        "",
        "| Source | Step | Client | Status | Bytes | Challenge | Payload | Result |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        *detail,
    ]
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
