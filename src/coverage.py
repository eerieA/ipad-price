"""Did each source actually get polled? (plan.md §7, §8).

Computed from the observation log, never from a success flag: a poller that
dies before writing has no say in whether it ran. Per source, because the
Actions and desktop runners fail independently, and a blocked source writes
nothing (poll.py refuses to record zero listings), so a block shows up here as
missing polls.
"""

import math
from dataclasses import dataclass
from datetime import timedelta

import ranking


@dataclass(frozen=True)
class SourceCoverage:
    source: str
    polls: int           # schedule slots in the window with at least one run
    expected: int        # schedule slots in the window
    last: str | None     # observed_at of the latest run ever, None if never polled
    stale_hours: float | None  # set when `last` is older than the threshold


def measure(config, observations, now, settings):
    """One SourceCoverage per source with a fetcher (`client` in sources.yaml),
    plus any source that has observations without one."""
    runs = ranking.polls(observations)
    window_start = now - timedelta(days=settings["days"])
    slot_hours = 24 / settings["polls_per_day"]
    ids = sorted({s for s, cfg in config.sources.items() if "client" in cfg} | set(runs))

    result = []
    for source in ids:
        times = sorted(runs.get(source, ()))
        if not times:
            result.append(SourceCoverage(source, 0, 0, None, None))
            continue
        # A source added mid-window is expected from its first poll, not before.
        start = max(window_start, ranking.parse_stamp(times[0]))
        first_slot = _slot(start, slot_hours)
        polled = len({slot for t in times
                      if (slot := _slot(ranking.parse_stamp(t), slot_hours)) >= first_slot})
        expected = _slot(now, slot_hours) - first_slot + 1
        age = (now - ranking.parse_stamp(times[-1])).total_seconds() / 3600
        stale = age if age > settings["stale_after_hours"] else None
        result.append(SourceCoverage(source, polled, expected, times[-1], stale))
    return result


def _slot(moment, slot_hours):
    """Which schedule slot a moment falls in, counted from the epoch. Slots
    start at UTC midnight, like the cron hours, so a run that GitHub starts
    late still lands in its own slot, and a manual extra run in a slot that
    already has one adds nothing."""
    return math.floor(moment.timestamp() / 3600 / slot_hours)
