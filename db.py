# db.py
import sqlite3
import json

DB_FILE = "listings.db"

SCHEMA = """CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bhk TEXT,
    rent INTEGER,
    deposit INTEGER,
    sqft INTEGER,
    location TEXT,
    gated_community INTEGER,
    furnished TEXT,
    available_from TEXT,
    preferred_tenant TEXT,
    amenities TEXT,
    floor TEXT,
    maintenance INTEGER,
    parking TEXT,
    facing TEXT,
    lease_duration INTEGER,
    contact TEXT,
    listing_type TEXT,
    food_preference TEXT,
    gender_preference TEXT,
    no_brokerage INTEGER DEFAULT 0,
    raw_text TEXT UNIQUE,
    images TEXT,
    post_url TEXT,
    group_name TEXT,
    group_url TEXT,
    scraped_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

WISHLIST_SCHEMA = """CREATE TABLE IF NOT EXISTS wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER UNIQUE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id)
)"""

# Columns that might not exist in older DBs
MIGRATE_COLUMNS = [
    ("listing_type", "TEXT"),
    ("food_preference", "TEXT"),
    ("gender_preference", "TEXT"),
    ("no_brokerage", "INTEGER DEFAULT 0"),
    ("post_url", "TEXT"),
]


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.execute(WISHLIST_SCHEMA)
    # Migrate: add missing columns to existing DBs
    existing = {row[1] for row in conn.execute("PRAGMA table_info(listings)").fetchall()}
    for col, col_type in MIGRATE_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {col_type}")
    conn.commit()
    return conn


def is_cross_group_dupe(conn, listing: dict) -> bool:
    contact = listing.get("contact")
    bhk = listing.get("bhk")
    location = listing.get("location")
    if not contact or not bhk:
        return False
    row = conn.execute(
        "SELECT id FROM listings WHERE contact = ? AND bhk = ? AND location = ?",
        (contact, str(bhk), location)
    ).fetchone()
    return row is not None


def insert_listing(conn, listing: dict, group_name=None, group_url=None):
    if is_cross_group_dupe(conn, listing):
        return False
    try:
        conn.execute(
            """INSERT OR IGNORE INTO listings
            (bhk, rent, deposit, sqft, location, gated_community, furnished,
             available_from, preferred_tenant, amenities, floor, maintenance,
             parking, facing, lease_duration, contact, listing_type,
             food_preference, gender_preference, no_brokerage, raw_text,
             images, post_url, group_name, group_url, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                listing.get("bhk"),
                listing.get("rent"),
                listing.get("deposit"),
                listing.get("sqft"),
                listing.get("location"),
                listing.get("gated_community"),
                listing.get("furnished"),
                listing.get("available_from"),
                listing.get("preferred_tenant"),
                json.dumps(listing.get("amenities")) if listing.get("amenities") else None,
                listing.get("floor"),
                listing.get("maintenance"),
                listing.get("parking"),
                listing.get("facing"),
                listing.get("lease_duration"),
                listing.get("contact"),
                listing.get("listing_type"),
                listing.get("food_preference"),
                listing.get("gender_preference"),
                1 if listing.get("no_brokerage") else 0,
                listing.get("raw_text"),
                json.dumps(listing.get("images")) if listing.get("images") else None,
                listing.get("post_url"),
                group_name,
                group_url,
                listing.get("scraped_at"),
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"DB insert error: {e}")
        return False


def search_listings(conn, **filters):
    """
    Search listings with flexible filters.

    Supported filters:
        min_rent, max_rent, bhk, furnished, gated_community,
        listing_type, food_preference, gender_preference,
        no_brokerage, parking, location, has_contact, has_images,
        sort_by, limit
    """
    query = "SELECT * FROM listings WHERE 1=1"
    params = []

    if filters.get("min_rent"):
        query += " AND rent IS NOT NULL AND rent >= ?"
        params.append(filters["min_rent"])
    if filters.get("max_rent"):
        query += " AND rent IS NOT NULL AND rent <= ?"
        params.append(filters["max_rent"])
    if filters.get("bhk"):
        query += " AND bhk = ?"
        params.append(str(filters["bhk"]))
    if filters.get("furnished"):
        query += " AND furnished = ?"
        params.append(filters["furnished"])
    if filters.get("gated_community"):
        query += " AND gated_community = 1"
    if filters.get("listing_type"):
        query += " AND listing_type = ?"
        params.append(filters["listing_type"])
    if filters.get("food_preference"):
        query += " AND food_preference = ?"
        params.append(filters["food_preference"])
    if filters.get("gender_preference"):
        query += " AND gender_preference = ?"
        params.append(filters["gender_preference"])
    if filters.get("no_brokerage"):
        query += " AND no_brokerage = 1"
    if filters.get("parking"):
        query += " AND parking IS NOT NULL AND parking IN ('both', ?)"
        params.append(filters["parking"])
    if filters.get("location"):
        query += " AND LOWER(location) LIKE ?"
        params.append(f"%{filters['location'].lower()}%")
    if filters.get("has_contact"):
        query += " AND contact IS NOT NULL"
    if filters.get("has_images"):
        query += " AND images IS NOT NULL"
    if filters.get("has_rent"):
        query += " AND rent IS NOT NULL"

    sort = filters.get("sort_by", "created_at")
    valid_sorts = {"rent": "rent", "created_at": "created_at", "bhk": "bhk"}
    sort_col = valid_sorts.get(sort, "created_at")
    query += f" ORDER BY {sort_col} DESC"

    limit = filters.get("limit", 50)
    query += " LIMIT ?"
    params.append(limit)

    offset = filters.get("offset", 0)
    if offset:
        query += " OFFSET ?"
        params.append(offset)

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def count_listings(conn, **filters):
    """Count total matching listings for pagination."""
    query = "SELECT COUNT(*) FROM listings WHERE 1=1"
    params = []

    if filters.get("min_rent"):
        query += " AND rent IS NOT NULL AND rent >= ?"
        params.append(filters["min_rent"])
    if filters.get("max_rent"):
        query += " AND rent IS NOT NULL AND rent <= ?"
        params.append(filters["max_rent"])
    if filters.get("bhk"):
        query += " AND bhk = ?"
        params.append(str(filters["bhk"]))
    if filters.get("furnished"):
        query += " AND furnished = ?"
        params.append(filters["furnished"])
    if filters.get("gated_community"):
        query += " AND gated_community = 1"
    if filters.get("listing_type"):
        query += " AND listing_type = ?"
        params.append(filters["listing_type"])
    if filters.get("food_preference"):
        query += " AND food_preference = ?"
        params.append(filters["food_preference"])
    if filters.get("gender_preference"):
        query += " AND gender_preference = ?"
        params.append(filters["gender_preference"])
    if filters.get("no_brokerage"):
        query += " AND no_brokerage = 1"
    if filters.get("parking"):
        query += " AND parking IS NOT NULL AND parking IN ('both', ?)"
        params.append(filters["parking"])
    if filters.get("location"):
        query += " AND LOWER(location) LIKE ?"
        params.append(f"%{filters['location'].lower()}%")
    if filters.get("has_contact"):
        query += " AND contact IS NOT NULL"
    if filters.get("has_images"):
        query += " AND images IS NOT NULL"
    if filters.get("has_rent"):
        query += " AND rent IS NOT NULL"

    return conn.execute(query, params).fetchone()[0]


def add_to_wishlist(conn, listing_id: int, note: str = "") -> bool:
    try:
        conn.execute("INSERT OR IGNORE INTO wishlist (listing_id, note) VALUES (?, ?)",
                     (listing_id, note))
        conn.commit()
        return True
    except Exception:
        return False


def remove_from_wishlist(conn, listing_id: int):
    conn.execute("DELETE FROM wishlist WHERE listing_id = ?", (listing_id,))
    conn.commit()


def get_wishlist_ids(conn) -> set:
    rows = conn.execute("SELECT listing_id FROM wishlist").fetchall()
    return {row[0] for row in rows}


def get_wishlist_listings(conn):
    rows = conn.execute("""
        SELECT l.*, w.note as wishlist_note, w.created_at as wishlisted_at
        FROM listings l JOIN wishlist w ON l.id = w.listing_id
        ORDER BY w.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def get_stats(conn):
    """Return summary stats of the DB."""
    stats = {}
    stats["total"] = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    stats["with_rent"] = conn.execute("SELECT COUNT(*) FROM listings WHERE rent IS NOT NULL").fetchone()[0]
    stats["with_contact"] = conn.execute("SELECT COUNT(*) FROM listings WHERE contact IS NOT NULL").fetchone()[0]
    stats["with_images"] = conn.execute("SELECT COUNT(*) FROM listings WHERE images IS NOT NULL").fetchone()[0]
    stats["full_flat"] = conn.execute("SELECT COUNT(*) FROM listings WHERE listing_type = 'full_flat'").fetchone()[0]
    stats["flatmate"] = conn.execute("SELECT COUNT(*) FROM listings WHERE listing_type = 'flatmate'").fetchone()[0]
    stats["no_brokerage"] = conn.execute("SELECT COUNT(*) FROM listings WHERE no_brokerage = 1").fetchone()[0]
    stats["veg"] = conn.execute("SELECT COUNT(*) FROM listings WHERE food_preference = 'veg'").fetchone()[0]
    return stats
