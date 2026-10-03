"""Gates, effective price, per-key cheapest, changes and coverage (plan.md §1,
§2, §7), on small constructed logs. The config is the real one, so these also
pin the rules.yaml values the digest's arithmetic depends on.
"""

from datetime import datetime, timedelta, timezone

import pytest

import changes
import coverage
import ranking

CONFIG = ranking.Config()
NOW = datetime(2026, 10, 2, 15, 0, tzinfo=timezone.utc)
PENCIL = CONFIG.rules["pencil_cost"]

MINI_128 = "Refurbished iPad mini (A17 Pro) Wi-Fi 128GB - Purple"
MINI_128_CELL = "Refurbished iPad mini (A17 Pro) Wi-Fi + Cellular 128GB - Blue"
AIR_13_M4 = "13-inch iPad Air Wi‑Fi + Cellular 1TB - Blue"


def obs(listing, price, *, hours_ago=0, source="apple_refurb", title=MINI_128,
        part="FXN93CL/A", condition=None, in_stock=True, model_number=None):
    return {"observed_at": ranking.stamp(NOW - timedelta(hours=hours_ago)), "source": source,
            "listing_id": f"{source}:{listing}", "url": f"https://example.test/{listing}",
            "title": title, "price": price, "in_stock": in_stock,
            "condition_raw": condition or ("new" if source == "apple_new"
                                           else "Apple Certified Refurbished"),
            "seller": "Apple", "part_number": part, "model_number": model_number,
            "battery_pct": None, "ships_from": None}


# ── Gates (§1) ───────────────────────────────────────────────────────────────

def test_a_listing_passing_every_gate_is_a_candidate_priced_with_the_pencil():
    gated = ranking.gate(CONFIG, [obs("a", 709.0)])
    assert [c.effective_price for c in gated.candidates] == [709.0 + PENCIL]


# (observation, the dismissal reason it must be counted under)
DISMISSED = [
    (obs("m2", 999.0, title="Refurbished 11-inch iPad Pro Wi‑Fi 128GB (4th Generation)",
         part="FNYC3VC/A"), "out of scope"),
    (obs("us", 709.0, part="FXN93LL/A"), "not a Canadian unit"),
    (obs("mmwave", 709.0, part=None, model_number="A2996"), "not a Canadian unit"),
    # the A-number read from the title when no model number field is given
    (obs("mmwave-title", 709.0, part=None, title=MINI_128 + " (A2996)"), "not a Canadian unit"),
    (obs("sold", 709.0, in_stock=False), "out of stock"),
]


@pytest.mark.parametrize("o, reason", DISMISSED, ids=[o["listing_id"] for o, _ in DISMISSED])
def test_a_gate_failure_is_dismissed_quietly(o, reason):
    gated = ranking.gate(CONFIG, [o])
    assert (gated.candidates, gated.held, dict(gated.dismissed)) == ([], [], {reason: 1})


def test_a_condition_on_the_excluded_side_is_dismissed(monkeypatch):
    monkeypatch.setitem(CONFIG.sources["apple_refurb"], "conditions",
                        {"accepted": [], "excluded": ["Refurb Good"]})
    gated = ranking.gate(CONFIG, [obs("a", 709.0, condition="refurb  good")])
    assert dict(gated.dismissed) == {"condition below grade A": 1}


def test_a_condition_label_on_neither_side_is_held_not_dropped():
    gated = ranking.gate(CONFIG, [obs("a", 709.0, condition="Premium Plus")])
    assert gated.candidates == [] and len(gated.held) == 1
    assert "Premium Plus" in gated.held[0][1]


def test_an_unresolved_listing_is_held_with_the_parser_reason():
    gated = ranking.gate(CONFIG, [obs("a", 999.0, title="11-inch iPad Air Wi‑Fi 128GB - Blue",
                                      part=None)])
    assert gated.candidates == [] and len(gated.held) == 1


def test_an_unknown_label_on_an_out_of_scope_model_is_not_review_noise():
    gated = ranking.gate(CONFIG, [obs("m2", 999.0, condition="Premium Plus",
                                      title="Refurbished 11-inch iPad Pro Wi‑Fi 128GB (4th Generation)",
                                      part="FNYC3VC/A")])
    assert gated.held == [] and dict(gated.dismissed) == {"out of scope": 1}


def test_source_adjustment_is_added_to_the_effective_price(monkeypatch):
    monkeypatch.setitem(CONFIG.sources["apple_refurb"], "source_adjustment", 50)
    [candidate] = ranking.gate(CONFIG, [obs("a", 709.0)]).candidates
    assert candidate.effective_price == 709.0 + PENCIL + 50


# ── One row per key, budget split (§2, §7) ───────────────────────────────────

def test_the_cheapest_listing_leads_its_key_and_the_rest_are_a_count():
    candidates = ranking.gate(CONFIG, [obs("a", 749.0), obs("b", 709.0), obs("c", 729.0)]).candidates
    [(best, others)] = ranking.best_per_key(candidates)
    assert (best.listing_id, others) == ("apple_refurb:b", 2)


def test_a_cellular_unit_competes_with_the_wifi_unit_of_the_same_config():
    candidates = ranking.gate(CONFIG, [obs("wifi", 709.0),
                                       obs("cell", 689.0, title=MINI_128_CELL)]).candidates
    [(best, others)] = ranking.best_per_key(candidates)
    assert (best.listing_id, others) == ("apple_refurb:cell", 1)


def test_budget_is_compared_against_the_listing_price_not_the_effective_price():
    budget = CONFIG.rules["budget"]
    rows = ranking.best_per_key(ranking.gate(CONFIG, [
        obs("at", budget, title=MINI_128),
        obs("above", budget + 1, title="Refurbished iPad mini (A17 Pro) Wi-Fi 256GB - Blue"),
    ]).candidates)
    within, over = ranking.split_budget(CONFIG, rows)
    assert [r[0].listing_id for r in within] == ["apple_refurb:at"]
    assert [r[0].listing_id for r in over] == ["apple_refurb:above"]


# ── New-price reference (§2) ─────────────────────────────────────────────────

def test_the_new_reference_is_the_cheapest_new_listing_in_the_window():
    days = CONFIG.rules["new_reference_days"]
    log = [
        obs("new-a", 849.0, source="apple_new", title="iPad mini Wi‑Fi 128GB - Blue", part="MXN63CL/A"),
        obs("new-b", 829.0, source="apple_new", title="iPad mini Wi‑Fi 128GB - Purple",
            part="MXN93CL/A", hours_ago=24 * (days - 1)),
        # outside the window, and a refurb: neither counts
        obs("new-old", 799.0, source="apple_new", title="iPad mini Wi‑Fi 128GB - Blue",
            part="MXN63CL/A", hours_ago=24 * (days + 1)),
        obs("refurb", 709.0),
    ]
    assert ranking.new_references(CONFIG, log, NOW) == {("mini", "A17", 8.3, 128): (829.0, "apple_new")}


def test_a_foreign_new_unit_is_no_reference():
    log = [obs("us", 799.0, source="apple_new", title="iPad mini Wi‑Fi 128GB - Blue", part="MXN63LL/A")]
    assert ranking.new_references(CONFIG, log, NOW) == {}


# ── Changes since yesterday (§7) ─────────────────────────────────────────────

WINDOW = 24


def kinds(found):
    return sorted((ch.kind, ch.candidate.listing_id) for ch in found)


def test_appearance_price_moves_and_disappearance_are_reported():
    log = [obs("stays", 709.0, hours_ago=30), obs("drops", 829.0, hours_ago=30),
           obs("goes", 749.0, hours_ago=30),
           obs("stays", 709.0), obs("drops", 799.0), obs("arrives", 769.0)]
    found, first = changes.since(CONFIG, log, NOW, WINDOW)
    assert first == []
    assert kinds(found) == [("gone", "apple_refurb:goes"), ("new", "apple_refurb:arrives"),
                            ("price", "apple_refurb:drops")]
    [drop] = [ch for ch in found if ch.kind == changes.PRICE]
    assert drop.was == 829.0


def test_a_unit_that_came_and_went_inside_the_window_is_reported_gone():
    log = [obs("stays", 709.0, hours_ago=30),
           obs("stays", 709.0, hours_ago=18), obs("flash", 1519.0, hours_ago=18),
           obs("stays", 709.0, hours_ago=12), obs("flash", 1519.0, hours_ago=12),
           obs("stays", 709.0)]
    found, _ = changes.since(CONFIG, log, NOW, WINDOW)
    [gone] = found
    assert (gone.kind, gone.candidate.listing_id, gone.listed_hours) == ("gone", "apple_refurb:flash", 6)


def test_listed_hours_count_only_the_latest_unbroken_run():
    log = [obs("back", 709.0, hours_ago=60), obs("other", 729.0, hours_ago=54),
           obs("back", 709.0, hours_ago=30), obs("back", 709.0, hours_ago=24),
           obs("other", 729.0)]
    [gone] = [ch for ch in changes.since(CONFIG, log, NOW, WINDOW)[0] if ch.kind == changes.GONE]
    assert gone.listed_hours == 6


def test_a_source_with_no_poll_before_the_window_is_reported_once_not_as_all_new():
    found, first = changes.since(CONFIG, [obs("a", 709.0), obs("b", 729.0)], NOW, WINDOW)
    assert (found, first) == ([], ["apple_refurb"])


def test_a_dismissed_listing_coming_and_going_is_not_a_change():
    m2 = dict(title="Refurbished 11-inch iPad Pro Wi‑Fi 128GB (4th Generation)", part="FNYC3VC/A")
    log = [obs("stays", 709.0, hours_ago=30), obs("m2", 999.0, hours_ago=30, **m2),
           obs("stays", 709.0)]
    assert changes.since(CONFIG, log, NOW, WINDOW)[0] == []


# ── Coverage (§7, §8) ────────────────────────────────────────────────────────

SETTINGS = {"days": 7, "polls_per_day": 4, "stale_after_hours": 18}


def by_source(log):
    return {c.source: c for c in coverage.measure(CONFIG, log, NOW, SETTINGS)}


def test_coverage_counts_schedule_slots_from_a_sources_first_poll():
    # NOW is 15:00 UTC: runs at 03:00, 09:00 and 15:00 fill every slot since
    # the first run, and nothing before it is expected.
    log = [obs("a", 709.0, hours_ago=12), obs("a", 709.0, hours_ago=6), obs("a", 709.0),
           obs("a", 709.0, hours_ago=0.5)]   # a manual extra run adds nothing
    assert (by_source(log)["apple_refurb"].polls, by_source(log)["apple_refurb"].expected) == (3, 3)


def test_a_missed_slot_shows_as_a_gap():
    log = [obs("a", 709.0, hours_ago=12), obs("a", 709.0)]
    c = by_source(log)["apple_refurb"]
    assert (c.polls, c.expected) == (2, 3)


def test_a_source_silent_past_the_threshold_is_stale():
    c = by_source([obs("a", 709.0, hours_ago=19)])["apple_refurb"]
    assert c.stale_hours == pytest.approx(19)
    assert by_source([obs("a", 709.0, hours_ago=17)])["apple_refurb"].stale_hours is None


def test_a_source_with_a_fetcher_and_no_observations_is_never_polled():
    c = by_source([obs("a", 709.0)])["apple_new"]
    assert (c.polls, c.last) == (0, None)
