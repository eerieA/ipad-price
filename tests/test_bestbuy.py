"""The Best Buy fetcher on canned API responses (plan.md §3): which SKUs each
of its two sources keeps, which are fetched again, and what is recorded.
Shapes are trimmed from real responses; the sources config is the real one.
"""

import json

import pytest

import ranking
from sources import bestbuy

CONFIG = ranking.Config()
OWN, MARKETPLACE = CONFIG.sources["bestbuy"], CONFIG.sources["bestbuy_marketplace"]
SEARCH = "https://www.bestbuy.ca/api/v2/json/search?categoryid="
PRODUCT = "https://www.bestbuy.ca/api/v2/json/product/{}?lang=en-CA"
OFFERS = "https://www.bestbuy.ca/api/offers/v1/products/{}/offers"


def item(sku, name, price, seller=None):
    return {"sku": sku, "name": name, "salePrice": price, "productUrl": f"/en-ca/product/x/{sku}",
            "isMarketplace": seller is not None,
            "seller": seller and {"id": seller[0], "name": seller[1]}}


def product(condition, model_number, availability="InStock", brand="APPLE", price=None):
    return {"brandName": brand, "modelNumber": model_number, "salePrice": price,
            "availability": {"onlineAvailability": availability},
            "specs": [{"name": "Product Condition", "value": condition}]}


def offer(seller_id, name, price):
    return {"sellerId": seller_id, "sellerNameEn": name, "salePrice": price}


PRO_11 = 'Refurbished (Excellent) - Apple iPad Pro 11" 256GB with Wi-Fi (5th Generation) - Silver'
AIR_11 = 'Apple iPad Air M4 11" 128GB with Wi-Fi 7 (8th Generation) - Blue'


def fake_get(search_pages, details):
    """search_pages: category id → [page of items]; details: URL → payload.
    Any other URL fails the test: a request the fetcher should not make."""
    responses = {f"{SEARCH}{category}&lang=en-CA&pageSize=100&page={n}":
                 {"products": page, "totalPages": len(pages)}
                 for category, pages in search_pages.items() for n, page in enumerate(pages, 1)}
    responses.update(details)
    requested = []

    def get(url, expect):
        assert url in responses, f"unexpected request {url}"
        requested.append(url)
        return json.dumps(responses[url]).encode()
    return get, requested


def search(*items):
    return {"17154970": [list(items)], "17154972": [[]], "17154974": [[]]}


def test_own_stock_is_one_record_per_sku_at_the_product_price():
    get, _ = fake_get(search(item("1", AIR_11, 899.99)),
                      {PRODUCT.format("1"): product("Brand New", "MH314CL/A", price=879.99)})
    [record] = bestbuy.records(OWN, get, CONFIG.catalog)
    assert (record["listing_id"], record["price"], record["seller"], record["condition_raw"],
            record["part_number"], record["in_stock"]) == (
        "bestbuy:1:bbyca", 879.99, "Best Buy", "Brand New", "MH314CL/A", True)


def test_each_source_keeps_only_its_side_of_the_buy_box():
    page = search(item("1", AIR_11, 899.99), item("2", PRO_11, 999.0, seller=("7", "Tech Outlet")))
    get, requested = fake_get(page, {PRODUCT.format("1"): product("Brand New", "MH314CL/A", price=899.99)})
    assert [r["listing_id"] for r in bestbuy.records(OWN, get, CONFIG.catalog)] == ["bestbuy:1:bbyca"]
    assert PRODUCT.format("2") not in requested


def test_a_marketplace_sku_is_one_record_per_seller():
    get, _ = fake_get(search(item("2", PRO_11, 999.0, seller=("7", "Tech Outlet"))), {
        PRODUCT.format("2"): product("Refurbished Excellent", "MVV93CL/A"),
        OFFERS.format("2"): [offer("7", "Tech Outlet", 999.0), offer("8", "Price Slash", 989.0)]})
    found = bestbuy.records(MARKETPLACE, get, CONFIG.catalog)
    assert [(r["listing_id"], r["seller"], r["price"]) for r in found] == [
        ("bestbuy_marketplace:2:7", "Tech Outlet", 999.0),
        ("bestbuy_marketplace:2:8", "Price Slash", 989.0)]


@pytest.mark.parametrize("condition, availability", [("Refurbished Fair", "OnlineOnly"),
                                                     ("Refurbished Excellent", "SoldOut")])
def test_a_marketplace_sku_dismissed_whoever_sells_it_records_the_winner_without_asking_for_offers(
        condition, availability):
    get, _ = fake_get(search(item("2", PRO_11, 999.0, seller=("7", "Tech Outlet"))),
                      {PRODUCT.format("2"): product(condition, "MVV93CL/A", availability)})
    [record] = bestbuy.records(MARKETPLACE, get, CONFIG.catalog)
    assert (record["listing_id"], record["condition_raw"]) == ("bestbuy_marketplace:2:7", condition)


def test_an_out_of_scope_title_is_recorded_from_search_without_a_product_call():
    old = 'Refurbished (Excellent) - Apple iPad Air 2 9.7" screen 64GB - WiFi (2014 - A1566) Space Gray'
    get, _ = fake_get(search(item("3", old, 135.0, seller=("7", "Tech Outlet"))), {})
    [record] = bestbuy.records(MARKETPLACE, get, CONFIG.catalog)
    assert (record["title"], record["condition_raw"], record["part_number"]) == (old, None, None)


def test_carrier_plans_and_accessories_are_not_recorded():
    plan = 'TELUS Apple iPad Air M3 11" 128GB with Wi-Fi 6E & 5G (7th Generation) - Monthly Financing'
    get, _ = fake_get(search(item("4", plan, 41.63), item("5", "4 In 1 Flash Drive - 32GB USB Type C", 25.89)),
                      {PRODUCT.format("5"): product("Brand New", "JIEYAR-817", brand="BISBISOUS")})
    assert bestbuy.records(OWN, get, CONFIG.catalog) == []


def test_search_is_walked_to_its_last_page():
    pages = {"17154970": [[item("1", AIR_11, 899.99)], [item("6", AIR_11, 899.99)]],
             "17154972": [[]], "17154974": [[]]}
    get, _ = fake_get(pages, {PRODUCT.format(sku): product("Brand New", "MH314CL/A", price=899.99)
                              for sku in ("1", "6")})
    assert [r["listing_id"] for r in bestbuy.records(OWN, get, CONFIG.catalog)] == [
        "bestbuy:1:bbyca", "bestbuy:6:bbyca"]


@pytest.mark.parametrize("model_number, part, a_number", [
    ("MVV93CL/A", "MVV93CL/A", None),
    ("A2925", None, "A2925"),
    ("IPADAR1-32-GY-WF-RF", None, None),   # a seller's own code
])
def test_model_number_field_is_routed_to_part_or_a_number(model_number, part, a_number):
    get, _ = fake_get(search(item("1", AIR_11, 899.99)),
                      {PRODUCT.format("1"): product("Brand New", model_number, price=899.99)})
    [record] = bestbuy.records(OWN, get, CONFIG.catalog)
    assert (record["part_number"], record["model_number"]) == (part, a_number)
