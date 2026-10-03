"""Gates → effective price → the cheapest listing per key (plan.md §1, §2).

Shared by report.py and digest.py, so the console and the email can't rank
differently. Every observation is re-parsed on every run rather than read back
parsed, so a parser fix applies to all of history at once (§5).
"""

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

import conditions
import specs
from specs import OutOfScope, Resolved

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
OBSERVATIONS = ROOT / "data" / "observations"


class Config:
    def __init__(self, config_dir=CONFIG):
        def load(name):
            return yaml.safe_load((config_dir / name).read_text(encoding="utf-8"))
        self.catalog = specs.load_catalog(config_dir / "models.yaml")
        self.sources = {s["id"]: s for s in load("sources.yaml")["sources"]}
        self.rules = load("rules.yaml")
        self._parsed = {}

    def parse(self, o):
        """specs.parse, memoised: history repeats the same listings poll after poll."""
        fields = (o["title"], o["part_number"], o["model_number"])
        if fields not in self._parsed:
            self._parsed[fields] = specs.parse(self.catalog, fields[0], part_number=fields[1],
                                               model_number=fields[2])
        return self._parsed[fields]

    def short_name(self, source_id):
        return self.sources.get(source_id, {}).get("short", source_id)


@dataclass(frozen=True)
class Candidate:
    """A listing that passed every gate (§1)."""
    observation: dict
    resolved: Resolved
    effective_price: float

    @property
    def price(self):
        return self.observation["price"]

    @property
    def listing_id(self):
        return self.observation["listing_id"]


@dataclass
class Gated:
    candidates: list = field(default_factory=list)
    held: list = field(default_factory=list)            # (observation, reason)
    dismissed: Counter = field(default_factory=Counter)  # why → count, dropped quietly


# ── The log ──────────────────────────────────────────────────────────────────

def load_observations(directory=OBSERVATIONS):
    observations = []
    for path in sorted(Path(directory).glob("*/*.jsonl")):
        with path.open(encoding="utf-8") as file:
            observations.extend(json.loads(line) for line in file if line.strip())
    return observations


def polls(observations):
    """source → {observed_at → [observations]}, one entry per poll run."""
    by_source = defaultdict(lambda: defaultdict(list))
    for o in observations:
        by_source[o["source"]][o["observed_at"]].append(o)
    return by_source


def latest_poll(observations):
    """Each source's observations from its most recent run."""
    return [o for runs in polls(observations).values() for o in runs[max(runs)]]


# ── Gates and price ──────────────────────────────────────────────────────────

def gate(config, observations):
    """Sort one set of observations into candidates, held for review, and
    dismissed. Every gate that can dismiss runs before anything is held, so
    held means "could rank, if someone resolved it": an unknown label on an
    out-of-scope model, or an unresolved US unit, is not review noise."""
    gated = Gated()
    for o in observations:
        result = config.parse(o)
        verdict = conditions.classify(config.sources.get(o["source"], {}), o["condition_raw"])
        if isinstance(result, OutOfScope):
            gated.dismissed["out of scope"] += 1
        elif _foreign(config, o):
            gated.dismissed["not a Canadian unit"] += 1
        elif o["in_stock"] is False:
            gated.dismissed["out of stock"] += 1
        elif verdict == conditions.EXCLUDED:
            gated.dismissed["condition below grade A"] += 1
        elif not isinstance(result, Resolved):
            gated.held.append((o, result.reason))
        elif verdict == conditions.UNKNOWN:
            gated.held.append((o, f"unknown condition label {o['condition_raw']!r}"))
        else:
            gated.candidates.append(Candidate(o, result, effective_price(config, o)))
    return gated


def _foreign(config, o):
    """The Canadian gate (§1): a US part number or a non-Canadian A-number."""
    part = (o["part_number"] or "").upper()
    if any(part.endswith(suffix) for suffix in config.rules["foreign_part_suffixes"]):
        return True
    numbers = ({o["model_number"].upper()} if o["model_number"]
               else {n.upper() for n in specs.A_NUMBER_RE.findall(specs.normalize(o["title"]))})
    return bool(numbers & config.catalog.non_canadian)


def effective_price(config, o):
    adjustment = config.sources.get(o["source"], {}).get("source_adjustment", 0)
    return o["price"] + adjustment


def best_per_key(candidates):
    """[(cheapest candidate, how many others share its key)], cheapest first.
    One row per key; the rest are a count, not rows (§7)."""
    by_key = defaultdict(list)
    for c in candidates:
        by_key[c.resolved.key].append(c)
    rows = []
    for group in by_key.values():
        group.sort(key=lambda c: (c.effective_price, c.listing_id))
        rows.append((group[0], len(group) - 1))
    return sorted(rows, key=lambda row: (row[0].effective_price, row[0].listing_id))


def split_budget(config, rows):
    """(within, over), against the listing price, not the effective price (§2)."""
    budget = config.rules["budget"]
    return ([r for r in rows if r[0].price <= budget],
            [r for r in rows if r[0].price > budget])


def new_references(config, observations, now):
    """key → (price, source): the cheapest new listing per key over the window.
    Never a launch price, and never Apple's refurb "Was" price (§2). Only
    listings that pass the gates count — a US unit's price is no reference."""
    cutoff = stamp(now - timedelta(days=config.rules["new_reference_days"]))
    recent = [o for o in observations if o["observed_at"] >= cutoff
              and conditions.is_new(config.sources.get(o["source"], {}), o["condition_raw"])]
    references = {}
    for c in gate(config, recent).candidates:
        best = references.get(c.resolved.key)
        if best is None or c.price < best[0]:
            references[c.resolved.key] = (c.price, c.observation["source"])
    return references


# ── Display ──────────────────────────────────────────────────────────────────

def describe_key(key):
    family, chip, size, storage = key
    storage = f"{storage // 1024}TB" if storage >= 1024 else f"{storage}GB"
    return f'{family.capitalize()} {size}" {chip} {storage}'


def money(amount):
    return f"${amount:,.0f}" if float(amount).is_integer() else f"${amount:,.2f}"


# observed_at's format (poll.py). Sortable as text, which the window checks rely on.
STAMP = "%Y-%m-%dT%H:%M:%SZ"


def stamp(moment):
    return moment.strftime(STAMP)


def parse_stamp(text):
    return datetime.strptime(text, STAMP).replace(tzinfo=timezone.utc)
