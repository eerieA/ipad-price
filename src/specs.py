"""Raw listing fields → a configuration key, or an explicit failure (plan.md §6).

Resolution order, most to least trustworthy: Apple part number, model number
(A-number), then facts read from the title. Each step names a catalog model or
passes to the next; nothing is defaulted. A listing ends up Resolved, OutOfScope
(a known model the gates exclude) or Unresolved (held for review).

How title facts select a model is documented in config/models.yaml, beside the
data it depends on.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

STORAGE_GB = {32, 64, 128, 256, 512, 1024, 2048}


@dataclass(frozen=True)
class Model:
    id: str
    in_scope: bool
    family: str
    chip: str | None
    size: float | None
    size_aliases: tuple
    years: tuple
    generations: tuple
    ram_gb: dict | None
    reason: str | None

    def accepts_size(self, size):
        return self.size is None or size in (self.size, *self.size_aliases)


@dataclass(frozen=True)
class Catalog:
    models: dict          # id → Model
    by_part: dict         # part core (part number minus its first letter) → id
    by_model_number: dict  # A-number → (id, connectivity or None)
    sizes: frozenset      # every size a title may state
    non_canadian: frozenset  # A-numbers that fail the Canadian gate (§1)

    @property
    def in_scope(self):
        return {id_ for id_, model in self.models.items() if model.in_scope}


@dataclass(frozen=True)
class Resolved:
    model_id: str
    family: str
    chip: str
    size: float
    storage_gb: int
    connectivity: str | None
    ram_gb: int

    @property
    def key(self):
        # Connectivity is deliberately absent: a cellular unit competes with the
        # Wi-Fi unit of the same config (§2).
        return (self.family, self.chip, self.size, self.storage_gb)


@dataclass(frozen=True)
class OutOfScope:
    model_ids: tuple
    reason: str


@dataclass(frozen=True)
class Unresolved:
    reason: str


# ── Catalog ──────────────────────────────────────────────────────────────────

def load_catalog(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    models, by_part, by_model_number = {}, {}, {}

    def index(table, key, value, what):
        if key in table and table[key] != value:
            raise ValueError(f"{what} {key} listed under both {table[key]} and {value}")
        table[key] = value

    for in_scope, section in ((True, data["models"]), (False, data["out_of_scope"])):
        for id_, entry in (section or {}).items():
            models[id_] = _model(id_, in_scope, entry)
            for part in entry.get("parts", []):
                index(by_part, part_core(part), id_, "part")
            for number, connectivity in _model_numbers(entry.get("model_numbers", [])):
                index(by_model_number, number, (id_, connectivity), "model number")

    sizes = frozenset(s for m in models.values() if m.size for s in (m.size, *m.size_aliases))
    non_canadian = frozenset(n for entry in data["models"].values()
                             for n in entry.get("model_numbers", {}).get("non_canadian", []))
    return Catalog(models, by_part, by_model_number, sizes, non_canadian)


def _model(id_, in_scope, entry):
    return Model(
        id=id_, in_scope=in_scope, family=entry["family"], chip=entry.get("chip"),
        size=entry.get("size"), size_aliases=tuple(entry.get("size_aliases", ())),
        years=tuple(entry.get("years", ())), generations=tuple(entry.get("generations", ())),
        ram_gb=entry.get("ram_gb"), reason=entry.get("reason"))


def _model_numbers(numbers):
    """Out-of-scope entries give a flat list; in-scope ones split by connectivity."""
    if isinstance(numbers, list):
        return [(n, None) for n in numbers]
    connectivity = {"wifi": "wifi", "cellular": "cellular", "non_canadian": "cellular"}
    return [(n, connectivity[kind]) for kind, ns in numbers.items() for n in ns]


def part_core(part_number):
    """`MVW33CL/A` and `FVW33` → `VW33`: no region suffix, no new/refurb letter."""
    match = re.fullmatch(r"[A-Z]([A-Z0-9]{4})(?:[A-Z]{1,2}/A)?", part_number.strip().upper())
    return match.group(1) if match else None


# ── Parsing ──────────────────────────────────────────────────────────────────

class _Conflict(Exception):
    """The title states two different values for one fact."""


def parse(catalog, title, part_number=None, model_number=None):
    text = normalize(title)
    try:
        return _resolve(catalog, text, part_number, model_number)
    except _Conflict as conflict:
        return Unresolved(str(conflict))


def _resolve(catalog, text, part_number, model_number):
    identified = _identify(catalog, text, part_number, model_number)
    if isinstance(identified, (OutOfScope, Unresolved)):
        return identified
    model, connectivity = identified
    if not model.in_scope:
        return OutOfScope((model.id,), model.reason)

    storage = _single("storage", STORAGE_RE, text, _storage_gb)
    if storage is None:
        return Unresolved("no storage size in title")
    return Resolved(
        model_id=model.id, family=model.family, chip=model.chip, size=model.size,
        storage_gb=storage, connectivity=connectivity or _connectivity(text),
        ram_gb=model.ram_gb.get(storage, model.ram_gb["default"]))


def _identify(catalog, text, part_number, model_number):
    """(model, connectivity-or-None), or an OutOfScope / Unresolved outcome."""
    if part_number and (id_ := catalog.by_part.get(part_core(part_number))):
        return catalog.models[id_], None
    numbers = [model_number] if model_number else [m.upper() for m in A_NUMBER_RE.findall(text)]
    for number in numbers:
        if number in catalog.by_model_number:
            id_, connectivity = catalog.by_model_number[number]
            return catalog.models[id_], connectivity
    return _match_title(catalog, text)


def _match_title(catalog, text):
    family = _family(text)
    if family is None:
        return Unresolved("no iPad family in title")
    facts = {
        "size": (_single("size", SIZE_RE, text, lambda m: _size(m, catalog.sizes))
                 or _single("size", BARE_SIZE_RE, text, lambda m: _size(m, catalog.sizes))),
        "chip": _single("chip", CHIP_RE, text, lambda m: m.group(1).upper()),
        "generation": _single("generation", GENERATION_RE, text, lambda m: int(m.group(1) or m.group(2))),
        "year": _single("year", YEAR_RE, text, lambda m: int(m.group(1))),
    }
    candidates = [m for m in catalog.models.values() if family == m.family and _consistent(m, facts)]
    in_scope = [m for m in candidates if m.in_scope]
    if not candidates:
        return Unresolved(f"no catalog model matches {family} {facts}")
    if not in_scope:
        reasons = sorted({m.reason for m in candidates})
        return OutOfScope(tuple(m.id for m in candidates), "; ".join(reasons))
    if len(candidates) == 1:
        return candidates[0], None
    return Unresolved("ambiguous: " + ", ".join(m.id for m in candidates))


def _consistent(model, facts):
    """A fact contradicts a model only if the model declares that attribute."""
    return ((facts["size"] is None or model.accepts_size(facts["size"]))
            and (facts["chip"] is None or model.chip in (None, facts["chip"]))
            and (facts["generation"] is None or not model.generations
                 or facts["generation"] in model.generations)
            and (facts["year"] is None or not model.years or facts["year"] in model.years))


# ── Title facts ──────────────────────────────────────────────────────────────

_TYPOGRAPHY = str.maketrans({
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
    " ": " ", " ": " ",
    "‘": "'", "’": "'", "“": '"', "”": '"', "″": '"',
})


def normalize(title):
    """Lower-case, with typographic dashes, spaces and inch marks made plain.
    `''` (two apostrophes) is an inch mark in some Best Buy titles."""
    return title.translate(_TYPOGRAPHY).replace("''", '"').lower()


FAMILY_RE = re.compile(r"\bipad\s*(pro|air|mini)\b")
# "11-inch", '13"', "11 in.", "11in", "13 po" (French), "12,9 po"
SIZE_RE = re.compile(r"(?<![\d.,])(\d{1,2}(?:[.,]\d)?)\s*-?\s*(?:inch(?:es)?\b|in\b|\"|po\b|pouces?\b)")
# "iPad Pro 11 2024": a size straight after the family, with no unit
BARE_SIZE_RE = re.compile(r"\bipad (?:pro|air)\s+(\d{1,2}(?:\.\d)?)(?![\d.]|\s*(?:gb|go|tb|to)\b)")
CHIP_RE = re.compile(r"\b(m[1-9]|a1[0-9][xz]?)\b")
# "4th Generation", "2nd Gen.", "( 5th Generation )", "5e génération", and
# "iPad mini 4", the mini's own naming. Only the mini: "iPad Pro 11" is a size,
# and Air numbers past 5 are unofficial (§6). The lookahead keeps "mini 8.3" a size.
GENERATION_RE = re.compile(r"\b(\d{1,2})\s*(?:st|nd|rd|th|e|ème)\s*g[ée]n|\bipad mini (\d)\b(?![.,\d])")
YEAR_RE = re.compile(r"\b(20[12]\d)\b")
# "1TB", "256 Go", and Best Buy's "1TBGB"
STORAGE_RE = re.compile(r"\b(\d{1,4})\s*(gb|go|tb|to)(?:gb)?\b")
A_NUMBER_RE = re.compile(r"\b(a\d{4})\b")


def _family(text):
    if match := FAMILY_RE.search(text):
        return match.group(1)
    return "ipad" if re.search(r"\bipad\b", text) else None


def _single(fact, pattern, text, convert):
    """The one value a pattern finds in the title, or None."""
    values = {v for v in (convert(m) for m in pattern.finditer(text)) if v is not None}
    if len(values) > 1:
        raise _Conflict(f"title states more than one {fact}: " + ", ".join(map(str, sorted(values))))
    return values.pop() if values else None


def _size(match, known_sizes):
    size = float(match.group(1).replace(",", "."))
    size = int(size) if size.is_integer() else size
    return size if size in known_sizes else None


def _storage_gb(match):
    value = int(match.group(1)) * (1024 if match.group(2) in ("tb", "to") else 1)
    return value if value in STORAGE_GB else None


def _connectivity(text):
    if re.search(r"cellular|\blte\b|\b[45]g\b", text):
        return "cellular"
    if re.search(r"wi-?fi", text):
        return "wifi"
    return None
