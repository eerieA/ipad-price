"""Best Buy's JSON API → raw listing records (plan.md §3, §5).

One fetcher serves two sources, Best Buy's own stock and its marketplace
(sources.yaml says why); each keeps the SKUs whose buy-box winner is on its
side. Search shows only that winner, with no part number and no stock state,
so every SKU that could rank is fetched again on its own:

    product  the part number (`modelNumber`), the condition label, stock
    offers   every seller — marketplace only, since the winner is not always
             the cheapest

A SKU that is dismissed whatever those calls would say is not fetched again,
but is still recorded from what search showed: an observation can't be
backfilled (§4), and the digest's dismissed counts should see it.
"""

import json

import conditions
import specs

ORIGIN = "https://www.bestbuy.ca"
OWN_SELLER = ("bbyca", "Best Buy")

# Carrier plans are listed at their monthly payment: dropped, not parsed (§3).
CARRIER_PLAN = "Monthly Financing"


def records(source, get, catalog):
    steps = {role: [s for s in source["steps"] if s["role"] == role]
             for role in ("search", "product", "offers")}
    found = []
    for sku, item in _search(steps["search"], get).items():
        if item["isMarketplace"] != source["marketplace"] or CARRIER_PLAN in item["name"]:
            continue
        if isinstance(specs.parse(catalog, item["name"]), specs.OutOfScope):
            found.append(_record(source, item, _winner(item)))
            continue
        product = _get_json(get, steps["product"][0], sku)
        if product.get("brandName") != "APPLE":
            continue   # an accessory listed in an iPad category (§3)
        found.extend(_listings(source, item, product, steps["offers"][0], get))
    return found


def _search(search_steps, get):
    """sku → search item, over every page of every category."""
    items = {}
    for step in search_steps:
        page, pages = 1, 1
        while page <= pages:
            data = json.loads(get(f"{step['url']}&page={page}", step["expect"]))
            pages = data["totalPages"]
            items.update((item["sku"], item) for item in data["products"])
            page += 1
    return items


def _listings(source, item, product, offers_step, get):
    details = {
        "in_stock": product["availability"]["onlineAvailability"] != "SoldOut",
        "condition_raw": next((s["value"] for s in product.get("specs") or []
                               if s["name"] == "Product Condition"), None),
        **_identifiers(product.get("modelNumber")),
    }
    if not source["marketplace"]:
        return [_record(source, item, (*OWN_SELLER, product["salePrice"]), **details)]
    if not details["in_stock"] or conditions.classify(source, details["condition_raw"]) == conditions.EXCLUDED:
        # Dismissed whoever sells it, so the other sellers aren't asked for.
        return [_record(source, item, _winner(item), **details)]
    offers = _get_json(get, offers_step, item["sku"])
    return [_record(source, item, (o["sellerId"], o["sellerNameEn"], o["salePrice"]), **details)
            for o in offers]


def _identifiers(model_number):
    """Best Buy's `modelNumber` is usually Apple's part number (MVV93CL/A),
    sometimes an A-number (A2925), and sometimes a seller's own code, which is
    neither and is dropped."""
    value = (model_number or "").strip().upper()
    if specs.A_NUMBER_RE.fullmatch(value.lower()):
        return {"part_number": None, "model_number": value}
    return {"part_number": value if specs.part_core(value) else None, "model_number": None}


def _winner(item):
    """(seller id, seller name, price) of the offer search showed."""
    if item["isMarketplace"]:
        return item["seller"]["id"], item["seller"]["name"], item["salePrice"]
    return (*OWN_SELLER, item["salePrice"])


def _record(source, item, seller, in_stock=None, condition_raw=None,
            part_number=None, model_number=None):
    seller_id, seller_name, price = seller
    return {"source": source["id"], "listing_id": f"{source['id']}:{item['sku']}:{seller_id}",
            "url": ORIGIN + item["productUrl"], "title": item["name"], "price": float(price),
            "in_stock": in_stock, "condition_raw": condition_raw, "seller": seller_name,
            "part_number": part_number, "model_number": model_number,
            "battery_pct": None, "ships_from": None}


def _get_json(get, step, sku):
    return json.loads(get(step["url"].format(sku=sku), step["expect"]))
