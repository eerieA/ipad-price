# iPad Deal Tracker — Plan

## The actual goal

Buy one iPad good for Procreate drawing with a pressure-sensitive Apple Pencil, at the best price-to-quality available from Canadian retailers — new, refurbished or used — without babysitting retailer pages.

It is a filter that emails me once a day, not a price-intelligence platform.

This plan borrows its skeleton from `../mini-pc-price` (observation log, config-as-interface, GitHub Actions poll, coverage reporting) and is shaped by one difference: **marketplaces are out.** No eBay, Kijiji, Facebook, Back Market, Reebelo, Newegg third-party, or Amazon third-party/Renewed. That removes the whole seller-reputation layer mini-pc needed, and moves the hard part from *parsing chaotic listings* to *getting past bot defenses on big-box retailers* (§3, §8).

---

## 1. What counts as a candidate

Three gates. Failing any one excludes a listing at any price; each is binary for a reason no discount fixes.

| Gate | Why no price makes it acceptable |
| --- | --- |
| **Supports Apple Pencil Pro** | The only pressure-sensitive Pencil still sold new in Canada. Apple discontinued the Pencil 2 here (Jan 2026), and the USB-C Pencil has no pressure sensitivity, so it can't draw in Procreate. A model that only takes the Pencil 2 means buying a used Pencil from the marketplaces this plan excludes. |
| **Condition grade A or better, stated** | A drawing tablet is mostly screen. Ungraded listings are excluded, not guessed at — see the condition table below. |
| **Canadian unit** | Import risk: US-origin units carry customs fees, US warranty terms and, in the one sample we checked, a 41%-positive seller. Excluded when a listing shows a US part number (`LL/A` suffix), a US-only model number (e.g. mmWave A-numbers), or ships from outside Canada. Where origin is simply not stated, the listing stays in and the digest marks it `origin?`. |

### The model catalog this produces

The Pencil Pro gate alone decides the lineup, so there is no separate
year floor — it would exclude nothing the gate doesn't already. (A 2020 floor
was agreed first; the Pencil Pro gate, adopted after, excludes a strict
superset.)

| Family | Sizes | Chip | RAM | Still sold new in CA |
| --- | --- | --- | --- | --- |
| iPad Pro (M4, 2024) | 11", 13" | M4 | 8 GB below 1 TB; 16 GB at 1–2 TB | No — refurb/clearance only |
| iPad Pro (M5, 2025) | 11", 13" | M5 | 12 GB below 1 TB; 16 GB at 1–2 TB | Yes |
| iPad Air (M2, 2024) | 11", 13" | M2 | 8 GB | No |
| iPad Air (M3, 2025) | 11", 13" | M3 | 8 GB | No |
| iPad Air (M4, 2026) | 11", 13" | M4 | 12 GB | Yes |

RAM is a derived field, never parsed: titles don't state it, and on the Pros it
follows storage. It matters because Procreate's layer limit scales with it.

Out-of-scope models are **listed** in `config/models.yaml` with their
identifiers, not merely absent. A 2022 M2 Pro or a 2022 M1 Air ("iPad Air 5th
generation") must resolve to *known, excluded* — silently — rather than to
*unknown*, which is a review item (§6). Otherwise every refurb M2 Pro becomes
digest noise.

### Condition: what counts as grade A

| Source | Accepted | Excluded |
| --- | --- | --- |
| Apple Certified Refurbished | all (single grade: new battery + outer shell, 1-yr warranty) | — |
| Best Buy (own stock) | new; `Geek Squad Open Box` ("cosmetically flawless", full warranty) | — |
| Best Buy Marketplace | `Refurbished Excellent` (1-yr warranty) | `Refurbished Good`/`Fair`; `Open Box` (marketplace, ungraded) |
| Orchard | `Like New` | `Very Good`, `Good` |
| Walmart (incl. marketplace) | title grade `A+`, `A`, `Excellent`, `Like New`, `Premium` | `B`, `Good`, `Fair`, `Used`; bare `Refurbished`/`Restored` (ungraded) |
| Amazon.ca, sold by Amazon | new; Amazon Resale `Used – Like New` (graded and sold by Amazon itself) | Resale `Very Good`/`Good`/`Acceptable`; everything sold by third parties, including all of Renewed |
| Costco, Staples | new | — |

A label on the excluded side is dropped quietly. A label on **neither** side —
a new vocabulary appearing — is held for review (§7) rather than dropped, so
a grade we have never seen can't vanish without anyone noticing.

---

## 2. The decision rule

### Rank by effective price, per configuration

```text
effective_price = listing_price
                + pencil_cost          -- Pencil Pro, $169 (config/rules.yaml)
                + source_adjustment    -- per source, default 0 (§3)
```

`pencil_cost` is the same for every in-scope model now that the gate requires
Pencil Pro, so it doesn't reorder anything. It stays because the number the
digest shows should be what the purchase actually costs. It becomes a
per-model value only if the gate ever loosens.

`source_adjustment` is mini-pc's device: a subjective dollar figure for how
much recourse a vendor offers if the unit is bad (warranty length, restocking
fees). Every source starts at `0`. One gets a non-zero value only with a stated
reason in `sources.yaml` — e.g. if Orchard's 90-day warranty is confirmed
against Apple's one year. It is a preference priced in dollars, not an
expected value.

Nothing else adds dollars. Nano-texture glass is worth $0 to me, so it
earns no premium, and ProMotion isn't a requirement.

### Configurations, not a quality score

The canonical key is **`(family, chip, size, storage)`**. Wi-Fi and cellular
share one key: a cellular unit competes with the Wi-Fi unit of the same config
and wins only if it's cheaper, since the modem is worth nothing to me. Colour
and nano-texture aren't in the key either.

The digest shows the cheapest listing per key. It **does not** rank an M2 Air
against an M4 Pro on a quality scale. mini-pc rejected weighted scores as
unfalsifiable, and the objection is stronger here: "is an M4 Pro worth $400
more than an M3 Air to me?" is the buying decision itself, not something a
tracker should decide on my behalf. So each row prints the specs that bear on
it (chip, RAM, screen) next to the price, and the judgement stays with the
reader.

### Is it cheap for what it is?

Each row carries a **new-price reference** for the same key: the cheapest new
price observed for it across all sources in the last 30 days, labelled with its
source. This is the "same price for the exact same config" test — a refurb row
at or above its own new reference is a bad deal whatever its absolute price.
Where nothing new is observed for a key (M4 Pro, M2/M3 Air), the column is
blank. It is never filled from a launch price: those are pre-June-2026-increase
figures and would flatter every listing.

Apple's refurb tiles carry a "Was" price. It is Apple's *earlier refurb* price,
not a new price, and is never used as a reference.

### Budget: a split, not a gate

`budget: 1000` in `rules.yaml` divides the digest into *within budget* and
*over budget*. It is compared against the **listing price**, not the effective
price: the $1,000 was stated about the iPad, and including the Pencil would
quietly lower it to $831. Nothing is dropped for price. Over budget is the near-miss
section: a listing that clears every gate but fails a soft criterion lands
there rather than disappearing, and budget is currently the only soft criterion.

### Battery health

Recorded when a source states it (Amazon's tier floors, the odd listing that
states a %), shown in the row, never priced. Most sources don't state it, and
a field missing on most rows can't be used to rank them.

---

## 3. Sources

Verified 2026-09-30, every request from a **residential** IP. Nothing has
been tested from a GitHub Actions runner yet — that is Phase 0 (§9), and until
it runs, the "Actions?" column is a prediction.

| Source | Sells | Fetch path | Bot defense seen | Actions? |
| --- | --- | --- | --- | --- |
| **Apple CA** — refurb | refurb | `/ca/shop/refurbished/ipad`, inline JSON `window.REFURB_GRID_BOOTSTRAP` (tiles with `partNumber`, `price.currentPrice.raw_amount`, `filters.dimensions`) | none | likely |
| **Apple CA** — new | new | `/ca/shop/buy-ipad/ipad-pro` and `/ipad-air`, inline analytics JSON (`products[].partNumber`, `price.fullPrice`) | none | likely |
| **Orchard** (getorchard.com) | refurb | Shopify `/collections/refurbished-ipad-pros/products.json`, `/collections/refurbished-tablets/products.json`; condition is a variant option | none | likely |
| **Costco** | new | hand-listed product URLs → JSON-LD `offers.price` | none seen | likely |
| **Best Buy** | new, open box, marketplace refurb | JSON API: `api/v2/json/search?categoryid=17154970` (Pro) / `17154972` (Air); `api/v2/json/product/{sku}` for `specs["Product Condition"]`; `api/offers/v1/products/{sku}/offers` for every seller | Akamai — HTML pages 403 even from residential; JSON passed | uncertain |
| **Staples** | new (clearance) | Shopify `search/suggest.json` / `products.json` | Cloudflare — plain HTTP 403; passes with `curl_cffi` Chrome impersonation | uncertain |
| **Walmart** | new, marketplace refurb | `/en/c/kp/refurbished-ipad` and seeded `/en/ip/<slug>/<id>` pages, `__NEXT_DATA__` JSON; condition only in title | PerimeterX — first cold request blocked; later requests with cookies served | unlikely |
| **Amazon.ca** | new + Amazon Resale, sold by Amazon only | seeded ASINs → offers panel `gp/product/ajax/aodAjaxMain/?asin=…`, keep offers sold by Amazon itself (Amazon.ca, or the Resale seller — its exact seller string on .ca is unverified, confirm in Phase 3) | Akamai proof-of-work on the first cold request | unlikely |

Notes that constrain the implementation:

- **Best Buy search returns only the buy-box winner.** A marketplace SKU is
  a shared catalog entry with several sellers, so every candidate SKU needs the
  offers call. Category results also mix in carrier monthly plans ($20–60 rows)
  and accessories, which are dropped before parsing. "Geek Squad Certified
  Refurbished" never appeared for iPads; Best Buy's own used stock is `Geek
  Squad Open Box`.
- **Costco's search is a POST to a Google Retail Search API** needing a client
  ID from the page and warehouse parameters that were guessed. Too brittle to
  depend on, so Costco is URL-seeded (`watch_urls.yaml`). It sells new units
  only, so it's there as a new-price reference.
- **Staples returns duplicate EN/FR entries** for one product; collapse them on
  SKU.
- **Robots.** Best Buy disallows `/en-ca/search` but not `/api/`; Walmart
  disallows `/en/search` and bare `/en/ip/*` but allows `/en/ip/*/*` and
  `/c/kp/`. The fetch paths above stay inside what robots allows. Amazon's
  Conditions of Use prohibit robots outright; that source runs at a handful of
  seeded ASINs a day. Dropping it would cost Amazon Resale, the only used
  stock Amazon grades and sells itself.
- **Amazon fallback.** If the offers panel can't be fetched, camelcamelcamel's
  amazon.ca RSS alerts (verified to serve `.xml` while its HTML is behind
  Cloudflare) tell me when the Amazon-sold price drops. That is a nudge to check
  by hand, not an observation. Keepa's API (~€49/month) is the paid route and is
  not planned.

### Excluded, with reasons

Kept as comments in `sources.yaml` too, so the decisions are visible where the
config is edited.

- **eBay, Kijiji, Facebook, Back Market, Reebelo** — too chaotic: seller
  quality varies per listing.
- **Amazon third-party and Renewed** — every Renewed offer is a third-party
  seller, and the sample showed US shipping with import fees.
- **Newegg** — Cloudflare blocks it even from residential, and it had one
  in-scope iPad (a $2,599 marketplace M5).
- **eTek** — carries no iPads.
- **Visions, Memory Express, London Drugs, Canada Computers, The Source** —
  unfetchable (Cloudflare 403 even impersonated, client-rendered, expired TLS)
  or no iPads. Revisit only if the core sources come up thin.

---

## 4. Architecture and where it runs

```text
  ┌─────────────────────────────┐    ┌─────────────────────────────┐
  │ GitHub Actions (schedule)   │    │ Desktop (Task Scheduler)    │
  │ sources that pass Phase 0   │    │ only sources Actions can't  │
  │                             │    │ reach — may be empty        │
  └──────────────┬──────────────┘    └──────────────┬──────────────┘
                 │ fetch → raw → parse              │
                 ▼                                  ▼
  data/observations/<source>/<YYYY-MM-DD>.jsonl   (committed, append-only)
                 │
                 │ digest.py, once a day, in Actions
                 ▼
  load all JSONL → in-memory SQLite → gate → rank → one email
```

### The observation log is text files, not a committed database

mini-pc commits `data/tracker.db` and noted the fix "if it ever matters" is
observations as text. It matters here from day one: if Phase 0 puts any source
on the desktop, **two machines write history**, and two writers of one
committed binary is a merge conflict that git can't resolve. Per-source,
per-day JSONL files make that impossible by construction: each runner only
ever writes its own sources' files, so `git pull --rebase` before push always
merges cleanly. The digest rebuilds SQLite in memory on every run, which at
this scale takes milliseconds.

Everything mini-pc said about why the log exists still holds: **an observation
cannot be backfilled**, so every run writes one record per listing whether or
not anything changed, and raw responses go to a git-ignored `data/raw/` so a
parser bug can be fixed against old bytes.

### Split runners, decided by evidence

Phase 0 fetches every source once from Actions and records what comes back.
Sources that pass run in Actions; the rest move to a desktop scheduled task
running the same `poll.py --sources …`. The desktop's known weakness — asleep
means that day is lost — is the reason mini-pc left it, so it gets only what
it must, and the coverage line (§7) shows its gaps.

### Schedule

- **Poll every 6 hours**, not daily. Apple refurb stock appears and sells out
  within hours; a once-daily poll would miss units entirely, not just see them
  late. Four small runs a day is well within politeness and Actions' free
  minutes.
- **Digest once a day**, 15:00 UTC (8:00 Pacific), in the run that follows the
  desktop's morning poll.
- GitHub cron is best-effort (late under load, occasionally skipped), and
  scheduled workflows are disabled after 60 days of repo inactivity. Neither
  announces itself; both show up in coverage.

### Always send the digest

mini-pc gates the send on change. This project sends daily, as CLAUDE.md's
purpose states, for two reasons. The horizon is weeks, not months, so the "stops
opening it" risk is smaller. And with Apple refurb and Best Buy open-box stock
turning over, a day where nothing moved is rare. A missing email is then itself
the failure signal, alongside the coverage line.

---

## 5. Observation record

One JSON object per listing per run:

```json
{"observed_at": "2026-10-02T15:04:11Z", "source": "bestbuy",
 "listing_id": "bestbuy:19185831:bbyca", "url": "https://www.bestbuy.ca/…",
 "title": "Open Box - Apple iPad Pro 11\" 256GB Wi-Fi & 5G (5th Gen)",
 "price": 1549.99, "in_stock": true, "seller": "Best Buy",
 "condition_raw": "Geek Squad Open Box", "part_number": null,
 "model_number": "…", "battery_pct": null, "ships_from": null}
```

`listing_id` is source-scoped and includes the seller where one SKU has
several (Best Buy offers). Parsed fields — family, chip, size, storage,
connectivity, condition class, key — are **not stored**: they're recomputed
from these raw fields every run, so a parser fix applies to all of history
at once rather than only to observations made after it.

---

## 6. Parsing

The parser's job is `raw fields → (family, chip, size, storage, connectivity)`
or one of two explicit failures: *known out-of-scope* or *unresolved*. It is
where the bugs will be, and where the tests go.

### Resolution order, most to least trustworthy

1. **Apple part number** (`MDWK4CL/A`, refurb `FVW33CL/A`) → exact config
   lookup in `models.yaml`. Suffix `CL/A` / `VC/A` is Canadian; `LL/A` fails
   the Canadian gate. Refurb parts swap the leading `M` for `F`.
2. **Model number** (`A2836` …) → family and connectivity; storage from the
   title.
3. **Source-structured fields** — Apple's `refurbClearModel` /
   `dimensionCapacity`, Orchard variant options, Best Buy `specs[]`.
4. **Title regex**, last.

Never default. A listing that resolves no further than "an iPad Air, chip
unknown" is **unresolved**, held out of the ranking, and listed for manual
lookup. Guessing M3 for an M2 Air flatters the listing by a generation, and
that error only surfaces after purchase.

### `config/models.yaml` shape

```yaml
ipad_pro_11_m4:
  family: pro
  chip: M4
  size: 11
  year: 2024
  ram_gb: {default: 8, "1024": 16, "2048": 16}
  model_numbers: {wifi: [A2836], cellular: [A2837, A3006]}
  part_prefixes: []     # filled from observed Apple pages, one source comment each
  aliases: ["11-inch iPad Pro (M4)", "iPad Pro 11 (7th gen)", "iPad Pro 11 2024"]
  pencil_pro: true

out_of_scope:           # resolve and dismiss quietly (§1)
  - {id: ipad_pro_11_m2, model_numbers: [A2759, A2761, A2435, A2762], reason: "Pencil 2 only"}
  - {id: ipad_air_5_m1, aliases: ["iPad Air (5th generation)"], reason: "M1, Pencil 2 only"}
```

### The traps `tests/test_specs.py` must cover

Table-driven cases, each one a real title shape seen in the research:

- **Air chip ambiguity.** Apple's own store titles omit the chip ("11-inch
  iPad Air Wi‑Fi 128GB - Blue"). "iPad Air 2024" = M2 but "iPad Pro 2024" = M4.
  Retailers' "Air 6th/7th gen" numbering is unofficial. Without a part or model
  number, chip-less Air titles are unresolved.
- **"12.9" means a pre-M4 Pro, except on an Air**, where the 13" measures
  12.9" diagonally. A "12.9-inch Pro" is out of scope; a "12.9-inch Air" is a
  13" M2 or later.
- **"4th generation"** is the 2022 11" M2 Pro, the 2020 12.9" A12Z Pro, or the
  whole 2020 product line in Apple's iPadOS 27 list. Always parse size and
  generation together — and every one of them is out of scope.
- **M4 Pro aliases**: "7th gen", "2024", mislabelled "12.9".
- **"iPad Air (5th generation)"** is M1 → known out-of-scope, not unresolved.
- **Nano-texture on a 256/512 GB Pro** is a listing error (it's a 1–2 TB
  option). Parse storage from the title and ignore the nano claim; the key
  doesn't include it.
- **Normalisation**: curly quotes and `″`; non-breaking hyphens (U+2011) in
  "11‑inch"; "Wi‑Fi+Cellular" / "Wi-Fi + Cellular" / "LTE" / "5G"; "Space
  Grey"/"Gray"; French Staples titles.
- **Bundles**: "with Apple Pencil" doesn't change the price math. A bundled
  USB-C Pencil is worthless for drawing, and a Pencil 2 bundled with an in-scope
  model is incompatible.
- **Condition extraction** from Walmart and Best Buy titles:
  "(Refurbished Excellent)", "Refurbished (Excellent) -", "- Refurbished
  Excellen" (truncated), "(Grade A+)", "Open Box (10/10 condition)" (a seller's
  own words on an ungraded listing → excluded).

---

## 7. Output: one email a day

```text
📱 iPad Digest — Oct 2    (Pencil Pro $169 included in every price)

  ── changed since yesterday ───────────────────────────────────
  + NEW     Air 11" M3 256GB    Best Buy Mkt  Refurb Excellent   $849 ($1,018 eff.)
  ↓ DROP    Pro 11" M4 256GB    Staples       new         $1,299 → $1,249
  − GONE    Pro 11" M4 512GB    Apple refurb  (sold out after 5h)

  ── within budget ($1,000) ────────────────────────────────────
  $1,018  Air 11" M3 256GB    8GB   Best Buy Mkt · Refurb Excellent · 1yr
                                     new ref: —
  $1,107  Air 11" M4 128GB   12GB   Costco · new
                                     new ref: $1,107 (Costco) — this is it

  ── over budget ───────────────────────────────────────────────
  $1,418  Pro 11" M4 256GB    8GB   Staples · new (clearance)       +1 more
                                     new ref: $1,418 (Staples) — beats Apple refurb cellular $1,688
  $2,028  Pro 13" M4 512GB    8GB   Apple refurb · 1yr
                                     new ref: —

  ── held for review (2) ───────────────────────────────────────
  ?  unresolved chip: "Apple iPad Air 11-inch 128GB Wi-Fi Blue" (Walmart)
  ?  unknown condition label "Premium Plus": … (Best Buy Mkt)

  ── coverage ─────────────────────────────────────────────────
  last 7 days: apple 28/28 polls · bestbuy 28/28 · orchard 27/28 · walmart (desktop) 19/28
  ⚠ staples: 0 products for 3 polls (was 14) — handle broken or blocked?
```

(Figures are illustrative, not observed.)

- **Changes first**, because they are why today's email differs from yesterday's. "Changed" means list price, stock or appearance — never effective price, which also moves when I edit `rules.yaml`.
- **One row per key**, cheapest listing only. Other listings for the same key appear as a count (`+2 more`), not rows.
- **Held for review** is where the parser and the condition table admit what they don't know (§1, §6).
- **Coverage** is computed from the observation files, never from a success flag, and per source, because the split runners fail independently.

---

## 8. Risks

**Bot blocking is the main risk, and it's per source.** Four of eight sources
showed a bot defense even from home. The failure mode is quiet: a block that
returns HTTP 200 with a challenge page or an empty result looks like "no
iPads today". Mitigations:

- **An empty or challenge response is a failure, never zero listings.** Each fetcher checks for its source's challenge markers (`bm-verify`, `/blocked`, `px-captcha`, `Just a moment`) and for zero products from a source that previously returned some. Shopify answers a wrong collection handle with `200 {"products": []}` — mini-pc learned this — so Orchard and Staples need the same check.
- A blocked source is logged, skipped, and shown in coverage. It never fails the run or blocks the digest.
- Politeness: 4 polls a day, a handful of requests per source per poll.

**Parser misresolution** — an M2 Air read as M3, or a 12.9" Pro read as an Air. Mitigated by the resolution order, by never defaulting, and by the test table (§6).

**Apple refurb stock turns over in hours**, so a 6-hour poll still misses some units. Accepted: this tracker is for finding the price level worth waiting for, not for sniping one unit. If a missed Apple refurb unit ever mattered, the fix is a more frequent Apple-only schedule — Apple is the one source with no bot defense.

**The catalog goes stale.** A new model launch (a likely autumn event) adds keys that `models.yaml` doesn't have. They surface as *unresolved*, which is the right failure — loud, not wrong.

---

## 9. Phasing

### Phase 0 — reachability probe

`scripts/probe.py`, run from Actions (`workflow_dispatch`) and from the
desktop: one request per source, recording status, byte count and which
challenge markers appear. The result goes in `research/probe-<date>.md` and
fills the "Actions?" column in §3 with evidence.

**Done when:** every source is placed as Actions, desktop, or dropped.

### Phase 1 — Apple end to end

Apple refurb + Apple new: fetch → raw → parse → JSONL → console report
(`report.py`). This proves the catalog and the parser on the cleanest source,
and the new-price reference comes with it. Write `models.yaml` and the
`test_specs.py` table first; Apple's titles and part numbers are the fixtures.

**Done when:** `report.py` prints every in-scope Apple tile resolved to a key,
out-of-scope tiles (iPad mini, M2 Pro) are dismissed quietly, and `pytest -q`
passes.

### Phase 2 — digest and schedule

`digest.py` (Gmail SMTP, reused from mini-pc), coverage, change section, the
Actions workflow on the 6-hour / daily schedule. The workflow's `force`-style
manual trigger stays, for proving the send path from a runner.

**Done when:** a digest arrives from an Actions run.

### Phase 3 — remaining sources

In order of expected value per unit of effort: **Best Buy** (the most
refurb/open-box inventory), **Orchard**, **Costco**, **Staples**, **Walmart**,
**Amazon**. Each lands with its challenge-marker check and a few parser
fixtures from its real titles. Sources Phase 0 placed on the desktop get the
Task Scheduler entry (`scripts/install-task.ps1`, adapted from mini-pc) at the
same time.

**Done when:** each placed source appears in coverage, and its listings either
rank or are held for review.

### Reuse from mini-pc

Copied and stripped, not shared as a library: `dotenv_lite.py`, `digest.py`'s SMTP path, `coverage.py` (re-pointed at per-source JSONL), the workflow's structure, and `install-task.ps1`. Not reused: `specs.py`, `ranking.py`'s upgrade math, `sellers`/`chassis`/`parts` config — the domain is different.

---

## 10. Layout

```text
ipad-price/
├── config/
│   ├── models.yaml         # catalog + out-of-scope models (§1, §6)
│   ├── sources.yaml        # fetch paths, conditions accepted, source_adjustment (§3)
│   ├── watch_urls.yaml     # seeded URLs: Costco, Walmart, Amazon ASINs
│   └── rules.yaml          # gates, budget, pencil_cost (§2)
├── data/
│   ├── observations/       # <source>/<date>.jsonl — committed, the history (§4)
│   └── raw/                # git-ignored fetch bytes (§4)
├── src/
│   ├── poll.py             # --sources …; fetch → raw → JSONL
│   ├── sources/            # one small fetcher per source: bytes → raw records
│   ├── specs.py            # raw fields → key, or out-of-scope / unresolved (§6)
│   ├── conditions.py       # condition_raw → accepted / excluded / unknown (§1)
│   ├── ranking.py          # gates, effective price, per-key cheapest (§2)
│   ├── report.py           # console (Phase 1)
│   ├── digest.py           # email (Phase 2)
│   ├── coverage.py         # per-source coverage from the log (§7, §8)
│   └── dotenv_lite.py
├── scripts/                # probe.py (Phase 0), install-task.ps1 (Phase 3)
├── .github/workflows/poll.yml
└── tests/test_specs.py     # the suite that matters
```

No Docker: the Actions runner and the desktop both run plain Python. Dependencies are `requests`, `pyyaml` and `curl_cffi` (Staples, and any other source Phase 0 shows needs a browser TLS fingerprint).

---

## 11. Open questions

- **Walmart marketplace with origin not stated.** Kept and marked `origin?` (§1). If that turns out to be most Walmart rows, the choice between excluding them and trusting them comes back.
