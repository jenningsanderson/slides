#!/usr/bin/env python3
"""
Demo: overturemaps GERS registry lookup — scripted mock for slides.

This script faithfully reproduces the output of:
  overturemaps gers 08f2832a30d4001703ef25b69c4af924
  overturemaps gers 08f2832a30d4001703ef25b69c4af924 -f geojson

Run with:
  python3 demos/gers_demo.py
Capture with:
  uv run slides capture "python3 demos/gers_demo.py" assets/gers-demo.json --title "Overture Maps — GERS lookup"
"""

import json
import sys
import time

GERS_ID   = "08f2832a30d4001703ef25b69c4af924"
RELEASE   = "2026-04-15.0"
FILEPATH  = (
    f"overturemaps-us-west-2/release/{RELEASE}"
    "/theme=places/type=place/part-00089-5e5a3e5f.c000.parquet"
)


def p(text="", delay=0.0):
    print(text, flush=True)
    if delay:
        time.sleep(delay)


# ── Step 1: registry lookup ───────────────────────────────────────────────────

p(f"$ overturemaps gers {GERS_ID}", delay=1.2)

p(f"Found GERS ID '{GERS_ID}' in release {RELEASE}")
p(f"  Version:     47")
p(f"  Filepath:    s3://{FILEPATH}")
p(f"  Bbox:        [-122.419463, 37.774842, -122.419463, 37.774842]")
p(f"  First seen:  2023-07-26.0")
p(f"  Last seen:   {RELEASE}")
p()
p(f"Registry lookup complete for GERS ID: {GERS_ID}")
p("To download the feature data, use -f/--format option.", delay=1.4)

# ── Step 2: feature download ──────────────────────────────────────────────────

p(f"$ overturemaps gers {GERS_ID} -f geojson", delay=1.8)

feature = {
    "type": "Feature",
    "id": GERS_ID,
    "geometry": {
        "type": "Point",
        "coordinates": [-122.419463, 37.774842],
    },
    "properties": {
        "id": GERS_ID,
        "version": 47,
        "updatetime": "2026-04-01T00:00:00",
        "names": {
            "primary": "Blue Bottle Coffee",
            "common": None,
        },
        "categories": {
            "primary": "coffee_shop",
            "alternate": ["cafe", "food_and_drink"],
        },
        "confidence": 0.9523,
        "addresses": [{
            "freeform": "66 Mint St",
            "locality": "San Francisco",
            "postcode": "94103",
            "region": "CA",
            "country": "US",
        }],
        "phones": ["+1 510-653-3394"],
        "websites": ["https://bluebottlecoffee.com"],
        "brand": {
            "names": {"primary": "Blue Bottle Coffee"},
            "wikidata": "Q2945685",
        },
    },
}

for line in json.dumps(feature, indent=2).splitlines():
    print(line, flush=True)
    time.sleep(0.012)

p()
p(f"1 feature · {RELEASE} · 2.1s")
