# reparse.py
import json
from parser import parse_listing

with open("listings.json") as f:
    old = json.load(f)

if not old:
    print("listings.json is empty, nothing to reparse")
    exit(1)

listings = []
for i, item in enumerate(old, 1):
    text = item["raw_text"]
    print(f"[{i}/{len(old)}] Parsing: {text[:60]}...")
    parsed = None
    try:
        parsed = parse_listing(text)
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")
    if parsed:
        parsed["raw_text"] = text
        listings.append(parsed)
    else:
        print(f"  FAILED")

# Only overwrite if we got results
if listings:
    with open("listings.json", "w") as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)
    print(f"\nDone: {len(listings)}/{len(old)} parsed")
else:
    print(f"\nAll {len(old)} failed. listings.json NOT overwritten.")
