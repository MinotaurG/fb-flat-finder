# app.py
"""Flask web UI for browsing flat listings."""
import json
import math
from flask import Flask, render_template, request, redirect, url_for, jsonify
from db import get_conn, search_listings, count_listings, get_stats, add_to_wishlist, remove_from_wishlist, get_wishlist_ids, get_wishlist_listings

app = Flask(__name__)
ITEMS_PER_PAGE = 12


def safe_json(val):
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


@app.route("/")
def index():
    conn = get_conn()
    stats = get_stats(conn)

    # Get wishlist IDs
    wishlist_ids = get_wishlist_ids(conn)

    # Read filters from query params
    filters = {}
    if request.args.get("min_rent"):
        filters["min_rent"] = int(request.args["min_rent"])
    if request.args.get("max_rent"):
        filters["max_rent"] = int(request.args["max_rent"])
    if request.args.get("bhk"):
        filters["bhk"] = int(request.args["bhk"])
    if request.args.get("location"):
        filters["location"] = request.args["location"]
    if request.args.get("furnished"):
        filters["furnished"] = request.args["furnished"]
    if request.args.get("listing_type"):
        filters["listing_type"] = request.args["listing_type"]
    if request.args.get("gated_community"):
        filters["gated_community"] = True
    if request.args.get("no_brokerage"):
        filters["no_brokerage"] = True
    if request.args.get("food_preference"):
        filters["food_preference"] = request.args["food_preference"]
    if request.args.get("gender_preference"):
        filters["gender_preference"] = request.args["gender_preference"]
    if request.args.get("parking"):
        filters["parking"] = request.args["parking"]
    if request.args.get("has_contact"):
        filters["has_contact"] = True
    if request.args.get("has_images"):
        filters["has_images"] = True
    if request.args.get("has_rent"):
        filters["has_rent"] = True

    sort_by = request.args.get("sort_by", "created_at")
    page = int(request.args.get("page", 1))

    total_count = count_listings(conn, **filters)
    total_pages = max(1, math.ceil(total_count / ITEMS_PER_PAGE))
    page = min(page, total_pages)
    offset = (page - 1) * ITEMS_PER_PAGE

    query_filters = {**filters, "sort_by": sort_by, "limit": ITEMS_PER_PAGE, "offset": offset}
    results = search_listings(conn, **query_filters)
    conn.close()

    # Parse JSON fields for template
    for r in results:
        r["images"] = safe_json(r.get("images"))
        r["amenities"] = safe_json(r.get("amenities"))

    # Clean filters for pagination links (strip page/sort_by)
    clean_filters = {k: v for k, v in request.args.items() if k not in ('page', 'sort_by')}

    return render_template("index.html",
                           listings=results,
                           stats=stats,
                           filters=clean_filters,
                           page=page,
                           total_pages=total_pages,
                           total_count=total_count,
                           sort_by=sort_by,
                           wishlist_ids=wishlist_ids)


@app.route("/wishlist")
def wishlist():
    conn = get_conn()
    stats = get_stats(conn)
    listings = get_wishlist_listings(conn)
    wishlist_ids = get_wishlist_ids(conn)
    for r in listings:
        r["images"] = safe_json(r.get("images"))
        r["amenities"] = safe_json(r.get("amenities"))
    conn.close()
    return render_template("index.html",
                           listings=listings,
                           stats=stats,
                           filters={},
                           page=1,
                           total_pages=1,
                           total_count=len(listings),
                           sort_by="created_at",
                           wishlist_ids=wishlist_ids,
                           is_wishlist=True)


@app.route("/api/wishlist/<int:listing_id>", methods=["POST"])
def toggle_wishlist(listing_id):
    conn = get_conn()
    ids = get_wishlist_ids(conn)
    if listing_id in ids:
        remove_from_wishlist(conn, listing_id)
        saved = False
    else:
        add_to_wishlist(conn, listing_id)
        saved = True
    conn.close()
    return jsonify({"saved": saved})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
