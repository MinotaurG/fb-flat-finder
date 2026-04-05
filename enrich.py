# enrich.py
"""Extract additional fields from raw_text using regex/keywords."""
import re


def classify_listing_type(text: str) -> str:
    """Classify as 'flatmate', 'full_flat', or 'room'."""
    t = text.lower()
    flatmate_signals = ["flatmate", "flat mate", "roommate", "room mate", "sharing", "shared room",
                        "looking for a", "replacement", "occupant", "vacancy in"]
    room_signals = ["single room", "1 room available", "private room", "room available",
                    "room for rent", "1 room in"]
    for s in flatmate_signals:
        if s in t:
            return "flatmate"
    for s in room_signals:
        if s in t:
            return "room"
    return "full_flat"


def classify_food_preference(text: str) -> str:
    """Detect veg/non-veg preference. Returns 'veg', 'non_veg', 'any', or None."""
    t = text.lower()
    # Check non-veg first (longer match)
    non_veg_signals = ["non-veg", "non veg", "nonveg", "no food restriction",
                       "no restriction on food", "all food habits welcome"]
    veg_signals = ["vegetarian", "veg only", "pure veg", "veg preferred",
                   "strictly veg", "veg food only", "satvik", "brahmin",
                   "jain food", "no non-veg", "no nonveg"]

    has_veg = any(s in t for s in veg_signals)
    has_nonveg = any(s in t for s in non_veg_signals)

    if has_veg and not has_nonveg:
        return "veg"
    if has_nonveg and not has_veg:
        return "non_veg"
    if has_veg and has_nonveg:
        return "any"
    return None


def classify_gender(text: str) -> str:
    """Detect gender preference. Returns 'female', 'male', or 'any'."""
    t = text.lower()
    female_signals = ["female only", "only female", "girls only", "only for female",
                      "only for girls", "female flatmate", "female roommate",
                      "looking for a female", "women only"]
    male_signals = ["male only", "only male", "boys only", "only for male",
                    "only for boys", "male flatmate", "male roommate",
                    "looking for a male", "men only"]

    if any(s in t for s in female_signals):
        return "female"
    if any(s in t for s in male_signals):
        return "male"
    return "any"


def detect_no_brokerage(text: str) -> bool:
    t = text.lower()
    signals = ["no broker", "no brokerage", "direct owner", "owner direct",
               "zero brokerage", "without broker", "broker free"]
    return any(s in t for s in signals)


def normalize_furnished(value: str) -> str:
    """Normalize furnished field to 'fully', 'semi', or 'unfurnished'."""
    if not value:
        return None
    v = value.lower().strip()
    if "unfurnish" in v:
        return "unfurnished"
    if "semi" in v:
        return "semi"
    if "full" in v or v == "furnished":
        return "fully"
    return None


def normalize_parking(value: str) -> str:
    """Normalize parking to 'car', 'bike', 'both', or None."""
    if not value:
        return None
    v = value.lower().strip()
    if v in ("both", "car and bike", "bike and car", "2 car"):
        return "both"
    if "car" in v:
        return "car"
    if v in ("bike", "two-wheeler", "2 wheeler"):
        return "bike"
    return None


def normalize_rent(value) -> int:
    """Clean rent value to integer. Returns None if invalid."""
    if value is None:
        return None
    if isinstance(value, int) and 1000 <= value <= 500000:
        return value
    if isinstance(value, str):
        # Handle "12000-14000" → take lower bound
        match = re.search(r'(\d{4,6})', str(value))
        if match:
            rent = int(match.group(1))
            if 1000 <= rent <= 500000:
                return rent
    return None


def normalize_bhk(value) -> str:
    """Clean BHK to just the number."""
    if not value:
        return None
    match = re.search(r'(\d)', str(value))
    return match.group(1) if match else None


def enrich_listing(listing: dict) -> dict:
    """Add all regex-based fields and normalize existing ones."""
    raw = listing.get("raw_text", "")

    listing["listing_type"] = classify_listing_type(raw)
    listing["food_preference"] = classify_food_preference(raw)
    listing["gender_preference"] = classify_gender(raw)
    listing["no_brokerage"] = detect_no_brokerage(raw)
    listing["furnished"] = normalize_furnished(listing.get("furnished"))
    listing["parking"] = normalize_parking(listing.get("parking"))
    listing["rent"] = normalize_rent(listing.get("rent"))
    listing["bhk"] = normalize_bhk(listing.get("bhk"))

    return listing
