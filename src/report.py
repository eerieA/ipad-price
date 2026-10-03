"""Console report of each source's latest poll (plan.md §9, Phase 1).

    python src/report.py

Every observation is re-parsed here rather than read back parsed, so a parser
fix applies to all of history at once (§5).
"""

import sys
from collections import defaultdict
from datetime import datetime, timezone

import ranking
from ranking import describe_key
from specs import OutOfScope, Resolved


def main():
    sys.stdout.reconfigure(encoding="utf-8")   # a piped Windows stdout is cp1252
    config = ranking.Config()
    observations = ranking.load_observations()
    if not observations:
        print("No observations yet. Run src/poll.py first.")
        return
    now = datetime.now(timezone.utc)
    current = ranking.latest_poll(observations)
    latest = {o["source"]: o["observed_at"] for o in current}
    references = ranking.new_references(config, observations, now)

    by_key, out_of_scope, unresolved = defaultdict(list), defaultdict(int), []
    for o in current:
        result = config.parse(o)
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
