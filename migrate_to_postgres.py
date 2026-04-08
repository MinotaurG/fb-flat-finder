# migrate_to_postgres.py
"""Migrate data from SQLite to PostgreSQL (Supabase)."""
import sqlite3
import json
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("Set DATABASE_URL in .env first")
    exit(1)

import psycopg2

# Read from SQLite
print("Reading from SQLite...")
sqlite_conn = sqlite3.connect("listings.db")
sqlite_conn.row_factory = sqlite3.Row
rows = sqlite_conn.execute("SELECT * FROM listings").fetchall()
listings = [dict(r) for r in rows]
sqlite_conn.close()
print(f"Found {len(listings)} listings in SQLite")

# Connect to Postgres
print("Connecting to Supabase...")
pg_conn = psycopg2.connect(DATABASE_URL, sslmode="require")
pg_conn.autocommit = True
cur = pg_conn.cursor()

# Create tables
cur.execute("""
CREATE TABLE IF NOT EXISTS listings (
    id SERIAL PRIMARY KEY,
    bhk TEXT, rent INTEGER, deposit INTEGER, sqft INTEGER, location TEXT,
    gated_community INTEGER, furnished TEXT, available_from TEXT,
    preferred_tenant TEXT, amenities TEXT, floor TEXT, maintenance INTEGER,
    parking TEXT, facing TEXT, lease_duration INTEGER, contact TEXT,
    listing_type TEXT, food_preference TEXT, gender_preference TEXT,
    no_brokerage INTEGER DEFAULT 0, raw_text TEXT UNIQUE, images TEXT,
    post_url TEXT, group_name TEXT, group_url TEXT, scraped_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS wishlist (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER UNIQUE REFERENCES listings(id),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# Insert listings
print("Migrating listings...")
inserted = 0
for listing in listings:
    try:
        cur.execute("""
            INSERT INTO listings
            (bhk, rent, deposit, sqft, location, gated_community, furnished,
             available_from, preferred_tenant, amenities, floor, maintenance,
             parking, facing, lease_duration, contact, listing_type,
             food_preference, gender_preference, no_brokerage, raw_text,
             images, post_url, group_name, group_url, scraped_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (raw_text) DO NOTHING
        """, (
            listing["bhk"], listing["rent"], listing["deposit"], listing["sqft"],
            listing["location"], listing["gated_community"], listing["furnished"],
            listing["available_from"], listing["preferred_tenant"], listing["amenities"],
            listing["floor"], listing["maintenance"], listing["parking"],
            listing["facing"], listing["lease_duration"], listing["contact"],
            listing.get("listing_type"), listing.get("food_preference"),
            listing.get("gender_preference"), listing.get("no_brokerage", 0),
            listing["raw_text"], listing["images"], listing.get("post_url"),
            listing["group_name"], listing["group_url"], listing["scraped_at"],
        ))
        inserted += 1
    except Exception as e:
        print(f"  Skip: {e}")

cur.close()
pg_conn.close()
print(f"Done! Migrated {inserted}/{len(listings)} listings to Supabase")
