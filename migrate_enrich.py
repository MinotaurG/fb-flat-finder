# migrate_enrich.py
"""Enrich existing listings with regex-based fields without re-scraping."""
from db import get_conn
from enrich import enrich_listing

conn = get_conn()
rows = conn.execute("SELECT id, raw_text, furnished, parking, rent, bhk FROM listings").fetchall()

updated = 0
for row in rows:
    listing = dict(row)
    enriched = enrich_listing(listing)

    conn.execute("""UPDATE listings SET
        listing_type = ?,
        food_preference = ?,
        gender_preference = ?,
        no_brokerage = ?,
        furnished = ?,
        parking = ?,
        rent = ?,
        bhk = ?
        WHERE id = ?""",
        (
            enriched["listing_type"],
            enriched["food_preference"],
            enriched["gender_preference"],
            1 if enriched["no_brokerage"] else 0,
            enriched["furnished"],
            enriched["parking"],
            enriched["rent"],
            enriched["bhk"],
            enriched["id"],
        ))
    updated += 1

conn.commit()
conn.close()
print(f"Enriched {updated} listings")
