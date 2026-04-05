# search.py
"""CLI tool to search and filter flat listings."""
import argparse
import json
from db import get_conn, search_listings, get_stats


def format_listing(listing, index):
    """Format a single listing for terminal display."""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  #{index}")

    # Core info
    bhk = listing.get("bhk") or "?"
    rent = f"Rs.{listing['rent']:,}" if listing.get("rent") else "Not mentioned"
    deposit = f"Rs.{listing['deposit']:,}" if listing.get("deposit") else "-"
    location = listing.get("location") or "Unknown"
    furnished = listing.get("furnished") or "-"

    lines.append(f"  {bhk} BHK | {furnished} | {location}")
    lines.append(f"  Rent: {rent} | Deposit: {deposit}")

    # Extra details
    details = []
    if listing.get("gated_community"):
        details.append("[Gated]")
    if listing.get("no_brokerage"):
        details.append("[No Broker]")
    if listing.get("food_preference"):
        details.append(f"[{listing['food_preference']}]")
    if listing.get("parking"):
        details.append(f"[Parking: {listing['parking']}]")
    if listing.get("floor"):
        details.append(f"[Floor {listing['floor']}]")
    if listing.get("maintenance"):
        details.append(f"[Maint: Rs.{listing['maintenance']:,}]")
    if listing.get("available_from"):
        details.append(f"[Avail: {listing['available_from']}]")
    if listing.get("listing_type"):
        details.append(f"[{listing['listing_type']}]")
    if listing.get("gender_preference") and listing["gender_preference"] != "any":
        details.append(f"[{listing['gender_preference']} only]")

    if details:
        lines.append(f"  {' | '.join(details)}")

    # Amenities
    if listing.get("amenities"):
        amenities = json.loads(listing["amenities"]) if isinstance(listing["amenities"], str) else listing["amenities"]
        if amenities:
            lines.append(f"  Amenities: {', '.join(amenities)}")

    # Contact & links
    if listing.get("contact"):
        lines.append(f"  Contact: {listing['contact']}")
    if listing.get("post_url"):
        lines.append(f"  Link: {listing['post_url']}")

    # Images count
    if listing.get("images"):
        imgs = json.loads(listing["images"]) if isinstance(listing["images"], str) else listing["images"]
        if imgs:
            lines.append(f"  Photos: {len(imgs)}")

    # Raw text preview
    raw = listing.get("raw_text", "")
    preview = raw[:150].replace("\n", " ")
    lines.append(f"  > {preview}...")

    lines.append(f"{'='*60}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Search flat listings")
    parser.add_argument("--min-rent", type=int, help="Minimum rent")
    parser.add_argument("--max-rent", type=int, help="Maximum rent")
    parser.add_argument("--bhk", type=int, help="Number of bedrooms (1, 2, 3)")
    parser.add_argument("--location", type=str, help="Location keyword (e.g. Kondapur)")
    parser.add_argument("--furnished", choices=["fully", "semi", "unfurnished"], help="Furnished type")
    parser.add_argument("--gated", action="store_true", help="Gated community only")
    parser.add_argument("--type", dest="listing_type", choices=["full_flat", "flatmate", "room"], help="Listing type")
    parser.add_argument("--veg", action="store_true", help="Vegetarian preferred")
    parser.add_argument("--no-broker", action="store_true", help="No brokerage only")
    parser.add_argument("--gender", choices=["female", "male", "any"], help="Gender preference")
    parser.add_argument("--parking", choices=["car", "bike", "both"], help="Parking type")
    parser.add_argument("--has-contact", action="store_true", help="Must have contact number")
    parser.add_argument("--has-images", action="store_true", help="Must have images")
    parser.add_argument("--sort", choices=["rent", "created_at", "bhk"], default="created_at", help="Sort by")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    parser.add_argument("--stats", action="store_true", help="Show DB stats only")

    args = parser.parse_args()
    conn = get_conn()

    if args.stats:
        stats = get_stats(conn)
        print(f"\n  Database Stats")
        print(f"  {'='*40}")
        for k, v in stats.items():
            print(f"    {k}: {v}")
        conn.close()
        return

    filters = {}
    if args.min_rent: filters["min_rent"] = args.min_rent
    if args.max_rent: filters["max_rent"] = args.max_rent
    if args.bhk: filters["bhk"] = args.bhk
    if args.location: filters["location"] = args.location
    if args.furnished: filters["furnished"] = args.furnished
    if args.gated: filters["gated_community"] = True
    if args.listing_type: filters["listing_type"] = args.listing_type
    if args.veg: filters["food_preference"] = "veg"
    if args.no_broker: filters["no_brokerage"] = True
    if args.gender: filters["gender_preference"] = args.gender
    if args.parking: filters["parking"] = args.parking
    if args.has_contact: filters["has_contact"] = True
    if args.has_images: filters["has_images"] = True
    filters["sort_by"] = args.sort
    filters["limit"] = args.limit

    results = search_listings(conn, **filters)
    conn.close()

    if not results:
        print("\n  No listings match your filters. Try relaxing some criteria.")
        return

    print(f"\n  Found {len(results)} listings")
    for i, listing in enumerate(results, 1):
        print(format_listing(listing, i))


if __name__ == "__main__":
    main()
