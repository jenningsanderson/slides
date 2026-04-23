"""
demo_script.py — simulates a two-step GERS registry lookup with realistic timing.
Used to generate example.json and example.gif.
"""
import time

print("-- Step 1: look up GERS ID in the registry")
print()
time.sleep(0.4)

print("CREATE OR REPLACE TABLE result AS")
print("  SELECT id, theme, type, path, bbox")
print("  FROM read_parquet('s3://overturemaps-us-west-2/registry/*.parquet')")
print("  WHERE id = '379baf1c-d0ab-47e8-b6f6-d9ea16392fb7';")
print()
time.sleep(1.8)

print("FROM result SELECT *;")
print()
time.sleep(0.5)

print("┌──────────────────────────────────────────┬────────┬───────┬──────────────────────────────────────────────────────┐")
print("│ id                                       │ theme  │ type  │ path                                                 │")
print("├──────────────────────────────────────────┼────────┼───────┼──────────────────────────────────────────────────────┤")
print("│ 379baf1c-d0ab-47e8-b6f6-d9ea16392fb7    │ places │ place │ theme=places/type=place/part-00012-abc123.zstd.parquet│")
print("└──────────────────────────────────────────┴────────┴───────┴──────────────────────────────────────────────────────┘")
print("1 row  ·  6.21 s")
print()
time.sleep(0.6)

print("-- Step 2: set variables from the table (no re-scan)")
print()
time.sleep(0.3)

print("SET VARIABLE path = (SELECT path FROM result);")
time.sleep(0.2)
print("SET VARIABLE bbox = (SELECT bbox FROM result);")
print()
time.sleep(0.5)

print("-- Step 3: fetch the exact feature using path + bbox as predicates")
print()
time.sleep(0.4)

print("SELECT id, names.primary AS name, categories.primary AS category,")
print("       confidence, addresses[1].freeform AS address")
print("FROM read_parquet('s3://overturemaps-us-west-2/release/2026-04-15.0/'")
print("                  || getvariable('path'))")
print("WHERE id = '379baf1c-d0ab-47e8-b6f6-d9ea16392fb7'")
print("  AND bbox.xmin >= getvariable('bbox').xmin;")
print()
time.sleep(2.3)

print("┌──────────────────────────────────────────┬──────────────────────┬──────────┬────────────┬────────────────────────────┐")
print("│ id                                       │ name                 │ category │ confidence │ address                    │")
print("├──────────────────────────────────────────┼──────────────────────┼──────────┼────────────┼────────────────────────────┤")
print("│ 379baf1c-d0ab-47e8-b6f6-d9ea16392fb7    │ Grand Hotel Baglioni │ hotel    │ 0.9978     │ Piazza dell'Unità Italiana │")
print("└──────────────────────────────────────────┴──────────────────────┴──────────┴────────────┴────────────────────────────┘")
print("1 row  ·  2.31 s")
