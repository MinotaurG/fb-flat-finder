# parser_regex.py
"""Regex-only parser for extracting listing fields from raw post text. No AI needed."""
import re
import unicodedata


def _normalize_text(text: str) -> str:
    """Normalize unicode fancy text to ASCII."""
    # Normalize unicode letters and digits (bold/italic math symbols etc)
    normalized = unicodedata.normalize('NFKD', text)
    # Keep ASCII + common symbols
    result = ""
    for ch in normalized:
        ascii_ch = ch.encode('ascii', 'ignore').decode('ascii')
        result += ascii_ch if ascii_ch else ch
    return result


def extract_bhk(text: str) -> str:
    """Extract BHK or RK value."""
    t = _normalize_text(text).lower()
    # 1RK, 1 rk
    rk_match = re.search(r'(\d)\s*rk\b', t)
    if rk_match:
        return "RK"
    # 2BHK, 2 bhk, 2.5bhk
    bhk_match = re.search(r'(\d(?:\.\d)?)\s*bhk\b', t)
    if bhk_match:
        val = bhk_match.group(1)
        return val if '.' in val else str(int(float(val)))
    return None


def extract_rent(text: str) -> int:
    """Extract monthly rent in INR."""
    t = _normalize_text(text).lower()
    # "Rent: Rs.18,500" or "Rent - 18500" or "rent 18,500/-"
    patterns = [
        r'rent\s*[:\-–]\s*(?:rs\.?|₹|inr)?\s*([\d,]+)',
        r'(?:rs\.?|₹|inr)\s*([\d,]+)\s*/?\s*(?:month|mo|pm|per\s*month)',
        r'rent\s+(?:is\s+)?(?:rs\.?|₹|inr)?\s*([\d,]+)',
        r'rent\s+(?:of\s+)?(?:flat\s+)?(?:rs\.?|inr)?\s*([\d,]+)',
        r'([\d,]+)\s*/?\s*(?:month|mo|pm)\b',
        r'(\d{1,2})[.\s]*k\s*(?:rent|per\s*month|/\s*month|pm)',
        r'rent\s*[:\-–]?\s*(\d{1,2})[.\s]*k\b',
        r'budget\s*[:\-–]?\s*(?:rs\.?|₹)?\s*([\d,]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, t)
        if match:
            val = match.group(1).replace(',', '')
            if val.replace('.', '').isdigit() and float(val) < 100:
                # "14k" or "14.5k" format
                return int(float(val) * 1000)
            try:
                rent = int(val)
                if 1000 <= rent <= 500000:
                    return rent
            except ValueError:
                continue

    # Handle range: "10-15k" or "10k-15k"
    range_match = re.search(r'(\d{1,2})\s*k?\s*[-–to]+\s*(\d{1,2})\s*k', t)
    if range_match:
        low = int(range_match.group(1)) * 1000
        if 1000 <= low <= 500000:
            return low

    return None


def extract_deposit(text: str) -> int:
    """Extract security deposit amount."""
    t = _normalize_text(text).lower()
    patterns = [
        r'deposit\s*[:\-–]\s*(?:rs\.?|₹|inr)?\s*([\d,]+)',
        r'(?:advance|security)\s*[:\-–]?\s*(?:rs\.?|₹|inr)?\s*([\d,]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, t)
        if match:
            val = match.group(1).replace(',', '')
            try:
                dep = int(val)
                if 1000 <= dep <= 1000000:
                    return dep
            except ValueError:
                continue
    return None


def extract_contact(text: str) -> str:
    """Extract Indian phone number."""
    t = _normalize_text(text)
    match = re.search(r'(?:\+91[\s-]?)?([6-9]\d{9})', t)
    return match.group(1) if match else None


def extract_location(text: str) -> str:
    """Extract location from known Hyderabad areas."""
    t = _normalize_text(text).lower()
    areas = [
        "kondapur", "gachibowli", "madhapur", "hitech city", "hi-tech city",
        "manikonda", "nanakramguda", "financial district", "kokapet",
        "narsingi", "tellapur", "nallagandla", "miyapur", "kukatpally",
        "kphb", "wipro circle", "banjara hills", "jubilee hills",
        "begumpet", "ameerpet", "sr nagar", "sanath nagar",
        "tolichowki", "mehdipatnam", "attapur", "rajendra nagar",
        "shamshabad", "lb nagar", "dilsukhnagar", "uppal",
        "secunderabad", "kompally", "bachupally", "nizampet",
        "pragathi nagar", "chandanagar", "lingampally", "gowlidoddy",
        "sheikhpet", "raidurg", "botanical garden", "mindspace",
        "hitec city", "serilingampally", "hafeezpet", "allwyn colony",
        "whitefields", "whitefield", "kismatpur", "bandlaguda",
        "peeramcheru", "mokila", "gopanpally", "khajaguda",
        "kothaguda", "raghavendra colony", "sriram nagar",
    ]
    found = []
    for area in areas:
        if area in t:
            found.append(area.title())
    return ", ".join(found[:3]) if found else None


def extract_furnished(text: str) -> str:
    """Extract furnished status."""
    t = _normalize_text(text).lower()
    if re.search(r'un\s*-?\s*furnish', t):
        return "unfurnished"
    if re.search(r'semi\s*-?\s*furnish', t):
        return "semi"
    if re.search(r'full\w*\s*-?\s*furnish', t):
        return "fully"
    return None


def extract_floor(text: str) -> str:
    """Extract floor number."""
    t = _normalize_text(text).lower()
    match = re.search(r'(\d{1,2})\s*(?:th|st|nd|rd)?\s*floor', t)
    return match.group(1) if match else None


def extract_maintenance(text: str) -> int:
    """Extract maintenance charge."""
    t = _normalize_text(text).lower()
    match = re.search(r'maintenance\s*[:\-–]?\s*(?:rs\.?|₹)?\s*([\d,]+)', t)
    if match:
        val = match.group(1).replace(',', '')
        try:
            m = int(val)
            if 100 <= m <= 50000:
                return m
        except ValueError:
            pass
    return None


def extract_parking(text: str) -> str:
    """Extract parking type."""
    t = _normalize_text(text).lower()
    has_car = bool(re.search(r'car\s*park', t))
    has_bike = bool(re.search(r'(?:bike|two.?wheeler|2.?wheeler)\s*park', t))
    if has_car and has_bike:
        return "both"
    if has_car:
        return "car"
    if has_bike:
        return "bike"
    if "parking" in t:
        return "car"
    return None


def extract_facing(text: str) -> str:
    """Extract facing direction."""
    t = _normalize_text(text).lower()
    match = re.search(r'(east|west|north|south)\s*[-\s]?\s*facing', t)
    return match.group(1) if match else None


def extract_sqft(text: str) -> int:
    """Extract area in square feet."""
    t = _normalize_text(text).lower()
    match = re.search(r'(\d{3,5})\s*(?:sq\.?\s*ft|sft|sqft|square\s*feet)', t)
    if match:
        val = int(match.group(1))
        if 100 <= val <= 50000:
            return val
    return None


def extract_available_from(text: str) -> str:
    """Extract availability date."""
    t = _normalize_text(text).lower()
    # "immediate" variants
    if re.search(r'immedia|ready\s*to\s*move|instant\s*move', t):
        return "immediate"
    # "1st May", "May 1", "1 May"
    months = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december"
    match = re.search(rf'(\d{{1,2}})\s*(?:st|nd|rd|th)?\s*(?:of\s+)?({months})', t)
    if match:
        return f"{match.group(1)} {match.group(2).title()}"
    match = re.search(rf'({months})\s*(\d{{1,2}})', t)
    if match:
        return f"{match.group(2)} {match.group(1).title()}"
    # "1st week of April"
    match = re.search(rf'(\d{{1,2}})(?:st|nd|rd|th)?\s*week\s*(?:of\s+)?({months})', t)
    if match:
        return f"Week {match.group(1)} of {match.group(2).title()}"
    return None


def extract_lease_duration(text: str) -> int:
    """Extract lease duration in months."""
    t = _normalize_text(text).lower()
    match = re.search(r'(\d{1,2})\s*months?\s*(?:lease|lock|agreement)', t)
    if match:
        return int(match.group(1))
    match = re.search(r'(?:lease|lock|agreement)\s*[:\-]?\s*(\d{1,2})\s*months?', t)
    if match:
        return int(match.group(1))
    return None


def extract_amenities(text: str) -> list:
    """Extract amenities mentioned in the post."""
    t = _normalize_text(text).lower()
    amenity_map = {
        "lift": r'\blift\b',
        "gym": r'\bgym\b',
        "swimming pool": r'swimming\s*pool',
        "security": r'\bsecurity\b|cctv',
        "power backup": r'power\s*backup|generator|dg\s*set',
        "balcony": r'\bbalcon',
        "parking": r'\bparking\b',
        "wifi": r'\bwifi\b|wi-fi',
        "ac": r'\bac\b|air\s*condition',
        "geyser": r'\bgeyser\b',
        "washing machine": r'washing\s*machine',
        "fridge": r'\bfridge\b|refrigerator',
        "ro": r'\bro\b|water\s*purifier',
        "modular kitchen": r'modular\s*kitchen',
    }
    found = []
    for name, pattern in amenity_map.items():
        if re.search(pattern, t):
            found.append(name)
    return found if found else None


def extract_gated_community(text: str) -> bool:
    """Detect if listing is in a gated community."""
    t = _normalize_text(text).lower()
    signals = [
        r'gated\s*(?:community|society|complex)',
        r'gated\s*apartment',
        r'apartment\s*complex',
        r'(?:prestige|aparna|my\s*home|mantri|smr|salarpuria|ramky|pbel|brigade)\s+\w+',
    ]
    return any(re.search(s, t) for s in signals)


def parse_listing_regex(text: str) -> dict:
    """Extract all fields from a listing using regex only."""
    return {
        "bhk": extract_bhk(text),
        "rent": extract_rent(text),
        "deposit": extract_deposit(text),
        "sqft": extract_sqft(text),
        "location": extract_location(text),
        "gated_community": extract_gated_community(text),
        "furnished": extract_furnished(text),
        "available_from": extract_available_from(text),
        "floor": extract_floor(text),
        "maintenance": extract_maintenance(text),
        "parking": extract_parking(text),
        "facing": extract_facing(text),
        "lease_duration": extract_lease_duration(text),
        "amenities": extract_amenities(text),
        "contact": extract_contact(text),
    }


if __name__ == "__main__":
    tests = [
        "1bhk semi furnished flat in Kondapur. Rent: 12,000. Contact: +91-9876543210",
        "1RK Fully Furnished Flat for Rent in Kondapur. Rent: 22,000/- (Negotiable)",
        "3BHK gated community at Prestige High Fields. 25k rent. 18th floor. East facing. Car parking.",
        "Looking for male replacement in 2bhk. Rent 14k. Deposit 28000. Available from 1st May. Lift, gym, swimming pool.",
        "2.5BHK semi furnished flat in Manikonda. Budget: 15-20k. No brokerage. Vegetarian preferred.",
    ]
    for t in tests:
        print(f"\nInput: {t[:80]}...")
        result = parse_listing_regex(t)
        for k, v in result.items():
            if v is not None:
                print(f"  {k}: {v}")
