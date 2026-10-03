"""Console report of each source's latest poll (plan.md §9, Phase 1).

    python src/report.py

Every observation is re-parsed here rather than read back parsed, so a parser
fix applies to all of history at once (§5).
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import specs
from specs import OutOfScope, Resolved

ROOT = Path(__file__).resolve().parents[1]
OBSERVATIONS = ROOT / "data" / "observations"
NEW_REFERENCE_DAYS = 30   # §2: "the cheapest new price observed … in the last 30 days"


def load_observations():
    observations = []
    for path in sorted(OBSERVATIONS.glob("*/*.jsonl")):
        with path.open(encoding="utf-8") as file:
            observations.extend(json.loads(line) for line in file if line.strip())
    return observations


def latest_poll(observations):
    """Each source's observations from its most recent run."""
    latest = {}
    for o in observations:
        latest[o["source"]] = max(latest.get(o["source"], ""), o["observed_at"])
    return [o for o in observations if o["observed_at"] == latest[o["source"]]], latest


def new_references(parsed, now):
    """key → (price, source): the cheapest new listing per key in the window.
    Never a launch price, and never Apple's refurb "Was" price (§2)."""
    cutoff = (now - timedelta(days=NEW_REFERENCE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    references = {}
    for o, result in parsed:
        if (isinstance(result, Resolved) and o["condition_raw"] == "new"
                and o["observed_at"] >= cutoff):
            best = references.get(result.key)
            if best is None or o["price"] < best[0]:
                references[result.key] = (o["price"], o["source"])
    return references


def parse_all(catalog, observations):
    return [(o, specs.parse(catalog, o["title"], part_number=o["part_number"],
                            model_number=o["model_number"])) for o in observations]


def describe_key(key):
    family, chip, size, storage = key
    storage = f"{storage // 1024}TB" if storage >= 1024 else f"{storage}GB"
    return f'{family.capitalize()} {size}" {chip} {storage}'


def main():
    catalog = specs.load_catalog(ROOT / "config" / "models.yaml")
    observations = load_observations()
    if not observations:
        print("No observations yet. Run src/poll.py first.")
        return
    now = datetime.now(timezone.utc)
    current, latest = latest_poll(observations)
    references = new_references(parse_all(catalog, observations), now)

    by_key, out_of_scope, unresolved = defaultdict(list), defaultdict(int), []
    for o, result in parse_all(catalog, current):
        if isinstance(result, Resolved):
            by_key[result.key].append((o, result))
        elif isinstance(result, OutOfScope):
            out_of_scope[o["source"]] += 1
        else:
            unresolved.append((o, result))

    print("Latest polls: " + ", ".join(f"{s} {t}" for s, t in sorted(latest.items())))
    resolved_count = sum(len(rows) for rows in by_key.values())
    print(f"\n── resolved: {resolved_count} listings, {len(by_key)} keys " + "─" * 30)
    for key in sorted(by_key):
        rows = sorted(by_key[key], key=lambda row: row[0]["price"])
        reference = references.get(key)
        reference = f"${reference[0]:,.2f} ({reference[1]})" if reference else "—"
        print(f"\n{describe_key(key)}   {rows[0][1].ram_gb}GB RAM   new ref: {reference}")
        for o, result in rows:
            print(f"  ${o['price']:>9,.2f}  {o['source']:<12}  {o['condition_raw']:<27}  {o['title']}")

    print("\n── out of scope, dismissed: "
          + (", ".join(f"{s} {n}" for s, n in sorted(out_of_scope.items())) or "none"))
    print(f"\n── held for review: {len(unresolved)} " + "─" * 30)
    for o, result in unresolved:
        print(f"  ?  {result.reason}: \"{o['title']}\" ({o['source']})")


if __name__ == "__main__":
    main()
