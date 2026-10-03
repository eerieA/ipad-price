"""condition_raw → accepted / excluded / unknown (plan.md §1).

The labels live per source in config/sources.yaml, because the same word means
different things at different vendors: Best Buy's own "Open Box" is graded,
its marketplace's is not (§1). Matching ignores case and spacing only; a label
that differs in anything else is a new vocabulary, and the point of `unknown`
is that a new vocabulary is held for review rather than dropped.
"""

ACCEPTED, EXCLUDED, UNKNOWN = "accepted", "excluded", "unknown"


def classify(source, condition_raw):
    labels = source.get("conditions", {})
    label = _plain(condition_raw)
    if is_new(source, condition_raw) or label in {_plain(a) for a in labels.get("accepted", [])}:
        return ACCEPTED
    if label in {_plain(e) for e in labels.get("excluded", [])}:
        return EXCLUDED
    return UNKNOWN


def is_new(source, condition_raw):
    """A label the source uses for new stock: what the new-price reference is
    built from (§2). Each source words it its own way ("new", "Brand New")."""
    new = source.get("conditions", {}).get("new", [])
    return _plain(condition_raw) in {_plain(n) for n in new}


def _plain(label):
    return " ".join((label or "").split()).casefold()
