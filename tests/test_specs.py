"""The parser table (plan.md §6): raw listing fields → a key, or an explicit
failure. Titles are real ones from Apple CA, Best Buy, Costco, Staples, Amazon
and Walmart unless marked "constructed" — those are §6 traps no captured title
happened to show.
"""

import random
from pathlib import Path

import pytest

import specs
from specs import OutOfScope, Resolved, Unresolved

CATALOG = specs.load_catalog(Path(__file__).resolve().parents[1] / "config" / "models.yaml")


def parse(title, part_number=None, model_number=None):
    return specs.parse(CATALOG, title, part_number=part_number, model_number=model_number)


# ── Resolves to a key ────────────────────────────────────────────────────────
# (title, part_number, model_id, storage_gb, connectivity)
RESOLVED = [
    # Apple refurb: chip in the title, refurb part number
    ("Refurbished iPad Pro 11-inch (M4) Wi-Fi + Cellular 512GB with Standard glass – Space Black",
     "FVW33CL/A", "ipad_pro_11_m4", 512, "cellular"),
    ("Refurbished iPad pro 11-inch (M4) Wi-Fi + Cellular 256GB with Standard glass – Space Black",
     "FVW13CL/A", "ipad_pro_11_m4", 256, "cellular"),
    ("Refurbished iPad Pro 13‑inch (M4) Wi-Fi 512GB with Standard glass – Silver",
     "FVX53CL/A", "ipad_pro_13_m4", 512, "wifi"),
    # Apple new: the title never names the chip, so the part number decides
    ("11-inch iPad Air Wi‑Fi 512GB - Space Gray", "MH3A4CL/A", "ipad_air_11_m4", 512, "wifi"),
    ("13-inch iPad Air Wi‑Fi + Cellular 1TB - Blue", "MH9T4CL/A", "ipad_air_13_m4", 1024, "cellular"),
    ("11-inch iPad Pro Wi‑Fi 256GB with standard glass - Space Black",
     "MDWK4CL/A", "ipad_pro_11_m5", 256, "wifi"),
    ("iPad mini Wi‑Fi + Cellular 256GB - Blue", "MXPW3CL/A", "ipad_mini_a17pro", 256, "cellular"),
    # the refurb mini: unlisted part, but the title names the chip
    ("Refurbished iPad mini (A17 Pro) Wi-Fi 128GB - Purple", "FXN93CL/A", "ipad_mini_a17pro", 128, "wifi"),
    # Best Buy minis
    ('Apple iPad mini 8.3" 256GB with Wi-Fi (7th Generation) - Space Grey',
     None, "ipad_mini_a17pro", 256, "wifi"),
    ("Refurbished (Excellent) - Apple iPad mini 8.3'' 512GB with Wi-Fi & 5G (7th Generation) - Starlight",
     None, "ipad_mini_a17pro", 512, "cellular"),
    # "mini 7": a generation straight after the family
    ("(Refurbished Excellent) Apple iPad Mini 7 (2024) 128GB - Purple (WiFi)",
     None, "ipad_mini_a17pro", 128, "wifi"),
    # constructed: the "8" of "mini 8.3" is a size, not a generation
    ('Apple iPad mini 8.3" (A17 Pro) 256GB Wi-Fi', None, "ipad_mini_a17pro", 256, "wifi"),
    # constructed: the new-stock form of an observed refurb part (F → M)
    ("11-inch iPad Pro Wi-Fi + Cellular 512GB", "MVW33CL/A", "ipad_pro_11_m4", 512, "cellular"),
    # Best Buy
    ('Apple iPad Pro M5 13" 256GB with Wi-Fi (8th Generation) - Space Black',
     None, "ipad_pro_13_m5", 256, "wifi"),
    ('(Brand New) Apple iPad Pro 13-inch M5 (2025) 256GB - Space Gray (WiFi + Cellular)',
     None, "ipad_pro_13_m5", 256, "cellular"),
    ("Apple iPad Pro 13-Inch (M4): Ultra Retina XDR Display, 256GB, Wi-Fi 6E + 5G Cellular with eSIM - Space Black",
     None, "ipad_pro_13_m4", 256, "cellular"),
    # chip-less, but 7th-gen 13" names one model under every numbering
    ('Apple iPad Pro 13" 256GB with Wi-Fi (7th Generation) Silver - Refurbished (Fair)',
     None, "ipad_pro_13_m4", 256, "wifi"),
    ('Apple iPad Air M4 11" 128GB with Wi-Fi 7 (8th Generation) - Blue',
     None, "ipad_air_11_m4", 128, "wifi"),
    ('Apple iPad Air M3 13" 128GB with Wi-Fi 6E & 5G (7th Generation) - Purple',
     None, "ipad_air_13_m3", 128, "cellular"),
    ('Brand New - Apple iPad Air 13" M2 1TB with Wi-Fi & 5G (6th Generation) - Starlight',
     None, "ipad_air_13_m2", 1024, "cellular"),
    # '' as an inch mark
    ("Open Box - Apple iPad Air 11'' (M2) 128GB with Wi-Fi (6th Generation) - Starlight",
     None, "ipad_air_11_m2", 128, "wifi"),
    # "1TBGB"
    ('Open Box - Apple iPad Pro 11" (M4) 1TBGB with Wi-Fi (5th Generation) - Space Black',
     None, "ipad_pro_11_m4", 1024, "wifi"),
    # RAM stated beside storage; size after the colour
    ('Open Box - Apple iPad Pro ( WiFi + 5G LTE) - Silver 13" Touchscreen Tablet - Silver '
     '(Apple M4 / 8 GB RAM / 256 GB eMMC / MacOS)', None, "ipad_pro_13_m4", 256, "cellular"),
    # Best Buy: chip-less titles, settled by the part number its product API
    # returns as `modelNumber` (§3)
    ('Refurbished (Good) - Apple iPad Pro 11" 256GB with Wi-Fi (5th Generation) - Silver',
     "MVV93CL/A", "ipad_pro_11_m4", 256, "wifi"),
    ('Refurbished (Excellent) - Apple iPad Pro 11" 2TB with Nano-Etched Glass, Wi-Fi & 5G (5th Generation) - Silver',
     "MWRT3CL/A", "ipad_pro_11_m4", 2048, "cellular"),
    ('Apple iPad Air 13" 512GB with Wi-Fi (6th Generation) - Space Grey',
     "MV2J3CL/A", "ipad_air_13_m2", 512, "wifi"),
    ('Refurbished (Excellent) - Apple iPad Air 11" 256GB with Wi-Fi & 5G (6th Generation) - Blue',
     "MUXJ3CL/A", "ipad_air_11_m2", 256, "cellular"),
    # Costco
    ("Apple iPad Air, 11 in. 128GB, Wi-Fi, M4 Chip, Built For Apple Intelligence",
     None, "ipad_air_11_m4", 128, "wifi"),
    # Staples, French
    ("Apple - iPad Air 13 po, Puce M3, Wi-Fi, 128 Go", None, "ipad_air_13_m3", 128, "wifi"),
    # constructed: the two rows above put the size straight after "iPad Air",
    # where the unit-less fallback reads it anyway; these pin the unit itself
    ("Apple iPad Air (M2) 11'' 128GB Wi-Fi", None, "ipad_air_11_m2", 128, "wifi"),
    ("Apple - iPad Air, Puce M3, 13 po, 128 Go", None, "ipad_air_13_m3", 128, None),
    # constructed: year as the only discriminator ("Air 2024" = M2, "Pro 2024" = M4)
    ("Apple iPad Pro 11 2024 256GB Wi-Fi", None, "ipad_pro_11_m4", 256, "wifi"),
    ("Apple iPad Air 11-inch 2024 128GB Wi-Fi Blue", None, "ipad_air_11_m2", 128, "wifi"),
    # constructed: "12.9" on an Air is the 13" (§6)
    ('Apple iPad Air 12.9" M2 256GB Wi-Fi', None, "ipad_air_13_m2", 256, "wifi"),
    # constructed: double-prime inch mark and non-breaking hyphen
    ("Apple iPad Air 11″ M3 256GB Wi‑Fi", None, "ipad_air_11_m3", 256, "wifi"),
    # constructed: nano-texture claimed on a 256GB is a listing error; storage wins
    ("Apple iPad Pro 11-inch (M4) 256GB Wi-Fi Nano-texture glass", None, "ipad_pro_11_m4", 256, "wifi"),
    # constructed: a bundled Pencil changes nothing
    ("Apple iPad Air 11-inch (M3) 128GB Wi-Fi with Apple Pencil (USB-C)", None, "ipad_air_11_m3", 128, "wifi"),
]


@pytest.mark.parametrize("title, part, model_id, storage, connectivity", RESOLVED,
                         ids=[row[0][:60] for row in RESOLVED])
def test_resolves_to_model_and_storage(title, part, model_id, storage, connectivity):
    result = parse(title, part_number=part)
    assert isinstance(result, Resolved), result
    assert (result.model_id, result.storage_gb, result.connectivity) == (model_id, storage, connectivity)


# ── Known and out of scope: dropped quietly ──────────────────────────────────
# (title, part_number)
OUT_OF_SCOPE = [
    # Apple refurb
    ("Refurbished 11-inch iPad Pro Wi‑Fi+Cellular 128GB Space Grey (4th Generation)", "FNYC3VC/A"),
    ("Refurbished 12.9-inch iPad Pro Wi-Fi + Cellular 128GB Space Gray (6th Generation)", "FP1X3VC/A"),
    # Best Buy
    ("Apple 2022 iPad Pro, 12.9-inch, 256GB - Space Gray (Certified Refurbished)", None),
    ('Open Box - Apple iPad Air 10.9" (M1) 256GB with Wi-Fi (5th Generation) - Pink', None),
    ('Bell Apple iPad Pro 12.9" 1TB with Wi-Fi & 4G LTE (4th Generation) -Silver -Monthly Financing', None),
    ('Apple iPad Pro 12.9" ( 5th Generation ) Apple M1 Chip / Wi-Fi / 2TB / Silver - - Brand New', None),
    ('Bell Apple iPad Pro 11" 128GB with Wi-Fi & 4G LTE (2nd Generation) -Space Grey -Monthly Financing', None),
    # Amazon
    ("iPad Pro 11in (2nd Gen.) - 256GB - WiFi - Space Gray (Renewed Premium)", None),
    # Walmart (title as in the seeded URL's slug): the model number decides
    ("Refurbished Apple iPad Pro 11 2022 A2759 WiFi 256GB Space Gray Grade A", None),
    # constructed, from §6: "iPad Air (5th generation)" is M1, not unresolved
    ("Apple iPad Air (5th generation) 64GB Wi-Fi", None),
    # constructed, from §6: a chip-less "12.9-inch Pro" is pre-M4
    ('Apple iPad Pro 12.9" 256GB Wi-Fi Space Gray', None),
    # constructed: the mini before the A17 Pro takes only the Pencil 2
    ("Apple iPad mini (6th generation) 64GB Wi-Fi Purple", None),
    # Best Buy: older minis numbered straight after the family
    ("Open Box-Apple iPad Mini 6 64GB Purple Wi-Fi 3J366V/A (Latest Model)", None),
    ("Refurbished (Excellent) Apple iPad Mini 5 (Cellular+Wifi) - 64GB - Silver", None),
    ("Refurbished (Good) - Apple iPad mini 4 128GB With Wi-Fi - Space Grey", None),
    ("Refurbished (Good) - Apple iPad Mini 2 16GB Space Gray Wi-Fi Only", None),
    # the A-number alone places it
    ("Refurbished (Good) - Apple iPad mini 2 32GB - WiFi (A1489) Silver", None),
    # Best Buy: 9.7" and first 12.9" models, by size and year
    ('Refurbished (Excellent) - Apple iPad Pro 9.7" screen 32GB - WiFi (2016 - A1673) Rose Gold - Certified Refurbished', None),
    ('Refurbished (Fair) - Apple iPad Pro (2015) 12.9" 128GB With Wi-Fi - Gold', None),
    ('Refurbished (Excellent) - Apple iPad Pro 12.9" 128GB with Wi-Fi (1st Generation) - Space Gray', None),
    ('Refurbished (Excellent) - Apple iPad Air 2 9.7" screen 64GB - WiFi (2014 - A1566) Space Gray - Certified Refurbished', None),
    ('Refurbished (Good) - Apple iPad Air 9.7" screen 32GB - WiFi (1st Gen. Late 2013 - A1474) Space Gray', None),
    # no size or year: the part number places it
    ("Refurbished (Excellent) - Apple iPad Air - 16GB - Wi-Fi - Space Grey", "MD785C/A"),
    # constructed: base iPads
    ("Apple iPad 11-inch (A16) Wi-Fi 128GB - Blue", None),
    ("Apple iPad (10th generation) 64GB Wi-Fi", None),
]


@pytest.mark.parametrize("title, part", OUT_OF_SCOPE, ids=[row[0][:60] for row in OUT_OF_SCOPE])
def test_known_out_of_scope_model_is_dismissed(title, part):
    assert isinstance(parse(title, part_number=part), OutOfScope)


# ── Unresolved: held for review, never guessed ───────────────────────────────
# (title, part_number)
UNRESOLVED = [
    # Apple's own chip-less title with no part number: M2, M3 or M4 (§6)
    ("11-inch iPad Air Wi‑Fi 128GB - Blue", None),
    # the plan's digest example (§7)
    ("Apple iPad Air 11-inch 128GB Wi-Fi Blue", None),
    # Air generation numbers are unofficial (§6)
    ('Apple iPad Air 13" 128GB with Wi-Fi (6th Generation) - Space Grey', None),
    # 11" Pro 5th gen: Best Buy's M4, or the Pro line's M1 — straddles the gate
    ('Open Box - Apple iPad Pro 11" 256GB with Wi-Fi & 5G (5th Generation) - Space Black', None),
    # no size: M3 11" or 13"
    ("Open Box - Apple iPad Air w/ Wi-Fi Touchscreen Tablet - Blue (Apple M3 / 8 GB RAM / 128 GB NVMe / MacOS)", None),
    # constructed: the A17 Pro and 6th-gen minis share the 8.3" screen
    ("Apple iPad mini 8.3-inch 256GB Wi-Fi Space Grey", None),
    # constructed: no storage
    ('Apple iPad Pro M4 11" Wi-Fi Space Black', None),
    # constructed: a part number the catalog doesn't know falls back to the title
    ("11-inch iPad Air Wi-Fi 128GB - Blue", "MZZZ4CL/A"),
    # constructed: an M4 Pro mislabelled 12.9" contradicts every catalog model
    ('Apple iPad Pro 12.9" M4 256GB Wi-Fi', None),
    # constructed: two storage sizes
    ('Apple iPad Air 11" M3 128GB 256GB Wi-Fi', None),
    # not an iPad at all
    ("Apple Pencil Pro", None),
]


@pytest.mark.parametrize("title, part", UNRESOLVED, ids=[row[0][:60] for row in UNRESOLVED])
def test_ambiguous_or_incomplete_listing_is_unresolved(title, part):
    assert isinstance(parse(title, part_number=part), Unresolved)


# ── Derived fields and the key ───────────────────────────────────────────────

@pytest.mark.parametrize("title, ram_gb", [
    ('Apple iPad Pro 11" (M4) 256GB Wi-Fi', 8),
    ('Apple iPad Pro 11" (M4) 1TB Wi-Fi', 16),
    ('Apple iPad Pro M5 13" 2TB Wi-Fi', 16),
    ('Apple iPad Pro M5 13" 512GB Wi-Fi', 12),
    ('Apple iPad Air M4 11" 128GB Wi-Fi', 12),
    ("Apple iPad mini (A17 Pro) 512GB Wi-Fi", 8),
])
def test_ram_follows_model_and_storage(title, ram_gb):
    assert parse(title).ram_gb == ram_gb


def test_cellular_and_wifi_of_one_config_share_a_key():
    wifi = parse('Apple iPad Air M3 11" 256GB with Wi-Fi 6E (7th Generation) - Blue')
    cellular = parse('Apple iPad Air M3 11" 256GB with Wi-Fi 6E & 5G (7th Generation) - Purple')
    assert wifi.key == cellular.key == ("air", "M3", 11, 256)


def test_model_number_field_sets_connectivity_the_title_omits():
    result = parse("Apple iPad Pro 11-inch 512GB Space Black", model_number="A2837")
    assert (result.model_id, result.connectivity) == ("ipad_pro_11_m4", "cellular")


def test_catalog_rejects_a_part_listed_under_two_models(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text(
        "models:\n"
        "  a: {family: pro, chip: M4, size: 11, ram_gb: {default: 8}, parts: [MVW33]}\n"
        "  b: {family: pro, chip: M4, size: 13, ram_gb: {default: 8}, parts: [FVW33]}\n"
        "out_of_scope: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="VW33"):
        specs.load_catalog(path)


# ── Property: any jumble of title fragments is classified, never crashes ─────

FRAGMENTS = [
    "Apple", "iPad", "Pro", "Air", "mini", "11-inch", '13"', "12.9”", "10.9''", "11 po",
    "M1", "M2", "M3", "M4", "M5", "A12Z", "2020", "2022", "2024", "2026",
    "128GB", "256 Go", "1TB", "2TBGB", "8 GB RAM", "Wi-Fi", "Wi‑Fi + Cellular", "5G",
    "(4th Generation)", "(7th gen.)", "5e génération", "Space Grey", "Refurbished (Excellent)",
    "A2836", "A9999", "Open Box", "-", "/", "(", ")",
]


def test_random_titles_always_classify():
    seed = random.randrange(2**32)
    rng = random.Random(seed)
    for _ in range(2000):
        title = " ".join(rng.choices(FRAGMENTS, k=rng.randint(0, 10)))
        result = parse(title)
        assert isinstance(result, (Resolved, OutOfScope, Unresolved)), f"seed={seed} title={title!r}"
        if isinstance(result, Resolved):
            assert result.model_id in CATALOG.in_scope, f"seed={seed} title={title!r}"
