"""Apple CA store pages → raw listing records (plan.md §3, §5).

Both pages embed their listings as inline JSON. Extraction raises when the
JSON is missing, so a layout change fails the source loudly (§8) instead of
reading as zero listings.
"""

import json
import re

ORIGIN = "https://www.apple.com"


def refurb_records(pages):
    """`window.REFURB_GRID_BOOTSTRAP` tiles. Apple drops a tile when the unit
    sells out, so every tile listed is in stock."""
    records = []
    for url, body in pages:
        grid = _json_after(body, r"window\.REFURB_GRID_BOOTSTRAP\s*=\s*", url)
        for tile in grid["tiles"]:
            records.append(_record(
                "apple_refurb", tile["partNumber"],
                url=ORIGIN + tile["productDetailsUrl"].split("?")[0],
                title=tile["title"],
                price=float(tile["price"]["currentPrice"]["raw_amount"]),
                in_stock=True,
                condition_raw="Apple Certified Refurbished"))
    return records


def new_records(pages):
    """The analytics `products[]` list on each buy page. It carries no stock
    state, so `in_stock` is unknown rather than assumed."""
    records = []
    for url, body in pages:
        for product in _json_after(body, r'"products":(?=\[\{"sku":)', url):
            records.append(_record(
                "apple_new", product["partNumber"],
                url=url,
                title=product["name"],
                price=float(product["price"]["fullPrice"]),
                in_stock=None,
                condition_raw="new"))
    return records


def _record(source, part_number, **fields):
    return {"source": source, "listing_id": f"{source}:{part_number}", **fields,
            "seller": "Apple", "part_number": part_number, "model_number": None,
            "battery_pct": None, "ships_from": None}


def _json_after(body, prefix_pattern, url):
    text = body.decode("utf-8")
    match = re.search(prefix_pattern, text)
    if not match:
        raise ValueError(f"no /{prefix_pattern}/ JSON in {url}")
    value, _ = json.JSONDecoder().raw_decode(text, match.end())
    return value
