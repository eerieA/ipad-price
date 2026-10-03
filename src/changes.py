"""What changed since yesterday (plan.md §7), read from the observation log.

mini-pc kept a snapshot of the last digest sent and diffed against it. Here the
baseline is each source's last poll before the window opened, so the log stays
the only state there is and nothing but observations gets committed (§4). The
cost: a digest that fails to send doesn't carry its changes into the next one.
That failure is loud — no email arrives — and the ranking below the changes is
complete either way.

"Changed" means list price, stock or appearance, never effective price, which
also moves when rules.yaml is edited (§7). Only gated candidates are compared:
an out-of-scope tile coming and going is not news.
"""

from dataclasses import dataclass
from datetime import timedelta

import ranking

NEW, PRICE, STOCK, GONE = "new", "price", "stock", "gone"


@dataclass(frozen=True)
class Change:
    kind: str
    candidate: ranking.Candidate  # the current listing; for GONE, as last seen
    was: float | None = None      # PRICE: the baseline price
    listed_hours: float | None = None  # GONE: first to last sighting of its last run


def since(config, observations, now, window_hours):
    """([Change], [sources with no poll before the window]).

    A source with no baseline is new to the log, and every listing in it would
    read as NEW; the digest says so once instead.
    """
    cutoff = ranking.stamp(now - timedelta(hours=window_hours))
    found, first = [], []
    for source, runs in sorted(ranking.polls(observations).items()):
        times = sorted(runs)
        before = [t for t in times if t <= cutoff]
        if not before:
            first.append(source)
            continue
        found.extend(_source_changes(config, runs, times, before[-1], cutoff))
    return found, first


def _source_changes(config, runs, times, baseline_time, cutoff):
    def candidates(time):
        return {c.listing_id: c for c in ranking.gate(config, runs[time]).candidates}

    baseline, current = candidates(baseline_time), candidates(times[-1])
    changes = []
    for listing_id, c in current.items():
        was = baseline.get(listing_id)
        if was is None:
            changes.append(Change(NEW, c))
        elif c.price != was.price:
            changes.append(Change(PRICE, c, was=was.price))
        elif None not in (c.observation["in_stock"], was.observation["in_stock"]) \
                and c.observation["in_stock"] != was.observation["in_stock"]:
            changes.append(Change(STOCK, c))

    # Gone includes what appeared and vanished inside the window: an Apple
    # refurb unit can sell out between two digests (§4).
    window = [t for t in times if t > cutoff]
    seen = dict(baseline)
    for time in window:
        seen.update(candidates(time))
    for listing_id, c in seen.items():
        if listing_id not in current:
            changes.append(Change(GONE, c, listed_hours=_listed_hours(runs, times, c)))
    return changes


def _listed_hours(runs, times, last_seen):
    """Hours from the first to the last poll of the listing's latest unbroken run."""
    end = times.index(last_seen.observation["observed_at"])
    start = end
    while start > 0 and any(o["listing_id"] == last_seen.listing_id for o in runs[times[start - 1]]):
        start -= 1
    return (ranking.parse_stamp(times[end]) - ranking.parse_stamp(times[start])).total_seconds() / 3600

