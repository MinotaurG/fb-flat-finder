# parser.py
import json
import re
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:4b"


def extract_phone(text: str) -> str:
    """Extract Indian phone number from text using regex."""
    # Normalize unicode digits to ASCII
    normalized = text.translate(str.maketrans('𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵', '0123456789'))
    match = re.search(r'(?:\+91[\s-]?)?([6-9]\d{9})', normalized)
    return match.group(1) if match else None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def parse_listing(text: str) -> dict:
    """Extract flat rental info from a Facebook post."""
    prompt = f"""Extract flat rental info as JSON with these exact keys. Use null for missing values.
{{"bhk":null,"rent":null,"deposit":null,"sqft":null,"location":null,"gated_community":null,"furnished":null,"available_from":null,"preferred_tenant":null,"amenities":null,"floor":null,"maintenance":null,"parking":null,"facing":null,"lease_duration":null,"contact":null}}

Rules:
- sqft: square feet of the flat (number only), not the locality name
- amenities: ONLY if words like lift, gym, security, power backup, balcony, swimming pool appear in the post. Do NOT guess.
- furnished: "fully", "semi", or "unfurnished"
- preferred_tenant: "family", "bachelor", or "any"
- floor: floor number (e.g. "18th floor" -> 18)
- maintenance: monthly maintenance in INR if mentioned separately from rent
- parking: "car", "bike", "both", or null
- facing: "east", "west", "north", "south", or null
- lease_duration: in months (e.g. "11 months" -> 11)
- contact: null (extracted separately)

Post: {text}"""

    raw = None
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 2048}
        }, timeout=180)
        resp.raise_for_status()
        raw = resp.json()["response"]
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group(0)) if match else None
        if result:
            result["contact"] = extract_phone(text)
        return result

    except json.JSONDecodeError:
        print(f"  ❌ JSON parse failed. Model said: {raw[:300]}")
        return None
    except Exception as e:
        print(f"  ⚠️ {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    sample_post = "1bhk semi furnished flat in Kondapur. Rent: ₹12,000. Contact: +91-XXXXXX"
    parsed = parse_listing(sample_post)
    print(f"Parsed: {parsed}")
