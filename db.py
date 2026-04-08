# db.py
import os
import json
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras
    DB_TYPE = "postgres"
else:
    import sqlite3
    DB_TYPE = "sqlite"
    DB_FILE = "listings.db"

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id SERIAL PRIMARY KEY,
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
);
CREATE TABLE IF NOT EXISTS wishlist (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER UNIQUE REFERENCES listings(id),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SQLITE_SCHEMA = """CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bhk TEXT, rent INTEGER, deposit INTEGER, sqft INTEGER, location TEXT,
    gated_community INTEGER, furnished TEXT, available_from TEXT,
    preferred_tenant TEXT, amenities TEXT, floor TEXT, maintenance INTEGER,
    parking TEXT, facing TEXT, lease_duration INTEGER, contact TEXT,
    listing_type TEXT, food_preference TEXT, gender_preference TEXT,
    no_brokerage INTEGER DEFAULT 0, raw_text TEXT UNIQUE, images TEXT,
    post_url TEXT, group_name TEXT, group_url TEXT, scraped_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

SQLITE_WISHLIST = """CREATE TABLE IF NOT EXISTS wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER UNIQUE, note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id)
)"""


def get_conn():
    if DB_TYPE == "postgres":
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(PG_SCHEMA)
        cur.close()
        return conn
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        conn.execute(SQLITE_SCHEMA)
        conn.execute(SQLITE_WISHLIST)
        conn.commit()
        return conn


def _execute(conn, query, params=None):
    """Execute a query, handling both SQLite and Postgres."""
    if DB_TYPE == "postgres":
        # Convert ? to %s for postgres
        query = query.replace("?", "%s")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params or [])
        return cur
    else:
        return conn.execute(query, params or [])


def _fetchall(conn, query, params=None):
    cur = _execute(conn, query, params)
    if DB_TYPE == "postgres":
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    else:
        return [dict(r) for r in cur.fetchall()]


def _fetchone(conn, query, params=None):
    cur = _execute(conn, query, params)
    if DB_TYPE == "postgres":
        row = cur.fetchone()
        cur.close()
        return row
    else:
        return cur.fetchone()


def is_cross_group_dupe(conn, listing: dict) -> bool:
    contact = listing.get("contact")
    bhk = listing.get("bhk")
    location = listing.get("location")
    if not contact or not bhk:
        return False
    row = _fetchone(conn,
        "SELECT id FROM listings WHERE contact = ? AND bhk = ? AND location = ?",
        (contact, str(bhk), location))
    return row is not None


def insert_listing(conn, listing: dict, group_name=None, group_url=None):
    if is_cross_group_dupe(conn, listing):
        return False
    try:
        insert_q = """INSERT INTO listings
            (bhk, rent, deposit, sqft, location, gated_community, furnished,
             available_from, preferred_tenant, amenities, floor, maintenance,
             parking, facing, lease_duration, contact, listing_type,
             food_preference, gender_preference, no_brokerage, raw_text,
             images, post_url, group_name, group_url, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        if DB_TYPE == "postgres":
            insert_q += " ON CONFLICT (raw_text) DO NOTHING"
        else:
            insert_q = insert_q.replace("INSERT INTO", "INSERT OR IGNORE INTO")

        _execute(conn, insert_q, (
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
        ))
        if DB_TYPE == "sqlite":
            conn.commit()
        return True
    except Exception as e:
        print(f"DB insert error: {e}")
        return False


def _build_filter_query(base, filters):
    """Build WHERE clauses from filters. Returns (query, params)."""
    query = base
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
        gp = filters["gender_preference"]
        if gp.startswith("not_"):
            query += " AND (gender_preference != ? OR gender_preference IS NULL)"
            params.append(gp.replace("not_", ""))
        else:
            query += " AND gender_preference = ?"
            params.append(gp)
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

    return query, params


def search_listings(conn, **filters):
    query, params = _build_filter_query("SELECT * FROM listings WHERE 1=1", filters)

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

    return _fetchall(conn, query, params)


def count_listings(conn, **filters):
    query, params = _build_filter_query("SELECT COUNT(*) as cnt FROM listings WHERE 1=1", filters)
    row = _fetchone(conn, query, params)
    if DB_TYPE == "postgres":
        return row["cnt"]
    else:
        return row[0]


def add_to_wishlist(conn, listing_id: int, note: str = "") -> bool:
    try:
        q = "INSERT INTO wishlist (listing_id, note) VALUES (?, ?)"
        if DB_TYPE == "postgres":
            q += " ON CONFLICT (listing_id) DO NOTHING"
        else:
            q = q.replace("INSERT INTO", "INSERT OR IGNORE INTO")
        _execute(conn, q, (listing_id, note))
        if DB_TYPE == "sqlite":
            conn.commit()
        return True
    except Exception:
        return False


def remove_from_wishlist(conn, listing_id: int):
    _execute(conn, "DELETE FROM wishlist WHERE listing_id = ?", (listing_id,))
    if DB_TYPE == "sqlite":
        conn.commit()


def get_wishlist_ids(conn) -> set:
    rows = _fetchall(conn, "SELECT listing_id FROM wishlist")
    return {row["listing_id"] for row in rows}


def get_wishlist_listings(conn):
    return _fetchall(conn, """
        SELECT l.*, w.note as wishlist_note, w.created_at as wishlisted_at
        FROM listings l JOIN wishlist w ON l.id = w.listing_id
        ORDER BY w.created_at DESC
    """)


def get_stats(conn):
    stats = {}
    stats["total"] = _fetchone(conn, "SELECT COUNT(*) as cnt FROM listings")["cnt"] if DB_TYPE == "postgres" else _fetchone(conn, "SELECT COUNT(*) FROM listings")[0]
    stats["with_rent"] = _fetchone(conn, "SELECT COUNT(*) as cnt FROM listings WHERE rent IS NOT NULL")["cnt"] if DB_TYPE == "postgres" else _fetchone(conn, "SELECT COUNT(*) FROM listings WHERE rent IS NOT NULL")[0]
    stats["with_contact"] = _fetchone(conn, "SELECT COUNT(*) as cnt FROM listings WHERE contact IS NOT NULL")["cnt"] if DB_TYPE == "postgres" else _fetchone(conn, "SELECT COUNT(*) FROM listings WHERE contact IS NOT NULL")[0]
    stats["with_images"] = _fetchone(conn, "SELECT COUNT(*) as cnt FROM listings WHERE images IS NOT NULL")["cnt"] if DB_TYPE == "postgres" else _fetchone(conn, "SELECT COUNT(*) FROM listings WHERE images IS NOT NULL")[0]
    stats["full_flat"] = _fetchone(conn, "SELECT COUNT(*) as cnt FROM listings WHERE listing_type = 'full_flat'")["cnt"] if DB_TYPE == "postgres" else _fetchone(conn, "SELECT COUNT(*) FROM listings WHERE listing_type = 'full_flat'")[0]
    stats["flatmate"] = _fetchone(conn, "SELECT COUNT(*) as cnt FROM listings WHERE listing_type = 'flatmate'")["cnt"] if DB_TYPE == "postgres" else _fetchone(conn, "SELECT COUNT(*) FROM listings WHERE listing_type = 'flatmate'")[0]
    stats["no_brokerage"] = _fetchone(conn, "SELECT COUNT(*) as cnt FROM listings WHERE no_brokerage = 1")["cnt"] if DB_TYPE == "postgres" else _fetchone(conn, "SELECT COUNT(*) FROM listings WHERE no_brokerage = 1")[0]
    stats["veg"] = _fetchone(conn, "SELECT COUNT(*) as cnt FROM listings WHERE food_preference = 'veg'")["cnt"] if DB_TYPE == "postgres" else _fetchone(conn, "SELECT COUNT(*) FROM listings WHERE food_preference = 'veg'")[0]
    return stats
