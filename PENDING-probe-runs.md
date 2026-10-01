# PENDING: more Actions probe runs

Phase 0 can't place sources until the probe has run from Actions on at least
two different days, or three if those two disagree (plan.md §9). Done so far:
**1 run** (`research/probe-2026-10-01-actions.md`).

## To do

1. On a later day, preferably at a different time of day from the last run,
   go to the repo's **Actions** tab → **probe** → **Run workflow**, or run
   `gh workflow run probe.yml`.
2. Copy the report from the run's summary page (or its `probe-<run id>`
   artifact) into `research/probe-<UTC date>-actions.md`. The date comes from
   the report's heading.
3. Repeat once more on another day, unless the two runs agree.
4. Hand it back to Claude: fill in the "Actions?" column in §3 and place each
   source.

Watch Walmart most closely. Its block comes and goes (plan.md §3), and its one
clean Actions pass so far doesn't settle where it runs.

Delete this file once the sources are placed.
