# parser_cascade.py
"""Cascade parser: regex first, finetuned model as fallback, keyword enrichment last."""
import json
import re
from parser_regex import parse_listing_regex
from enrich import enrich_listing

# Try to load finetuned model, gracefully degrade if unavailable
_model = None
_tokenizer = None


def _load_model():
    global _model, _tokenizer
    if _model is not None:
        return True
    try:
        from mlx_lm import load, generate
        _model, _tokenizer = load("flat-finder-model-fused")
        return True
    except Exception as e:
        print(f"Finetuned model unavailable: {e}")
        return False


def _query_model(text: str) -> dict:
    """Query the finetuned model for fields it's good at."""
    if not _load_model():
        return {}

    from mlx_lm import generate

    prompt = f"""Extract these fields from the flat rental post. Return JSON only.
Fields: gated_community (bool), furnished ("fully"/"semi"/"unfurnished"), available_from (date/string), amenities (list)
Use null for missing values.

Post: {text[:500]}"""

    try:
        messages = [
            {"role": "system", "content": "You extract flat rental info from Facebook posts. Return JSON only."},
            {"role": "user", "content": prompt},
        ]
        formatted = _tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        raw = generate(_model, _tokenizer, prompt=formatted, max_tokens=80, verbose=False)
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"Model inference error: {e}")
    return {}


def _pick_best(regex_val, model_val):
    """Pick the first non-null value."""
    if regex_val is not None and regex_val != False:
        return regex_val
    if model_val is not None and model_val != False:
        return model_val
    return regex_val


def parse_listing_cascade(text: str) -> dict:
    """Parse a listing using regex + finetuned model + keyword enrichment."""
    # Layer 1: Regex (fast, reliable for structured patterns)
    regex = parse_listing_regex(text)

    # Layer 2: Finetuned model (good for gated_community, furnished)
    model = _query_model(text)

    # Layer 3: Merge with best-source priority
    result = {
        # Regex-first fields
        "bhk": _pick_best(regex.get("bhk"), model.get("bhk")),
        "rent": _pick_best(regex.get("rent"), model.get("rent")),
        "deposit": _pick_best(regex.get("deposit"), model.get("deposit")),
        "sqft": _pick_best(regex.get("sqft"), model.get("sqft")),
        "contact": regex.get("contact"),
        "floor": _pick_best(regex.get("floor"), model.get("floor")),
        "maintenance": _pick_best(regex.get("maintenance"), model.get("maintenance")),
        "parking": _pick_best(regex.get("parking"), model.get("parking")),
        "facing": _pick_best(regex.get("facing"), model.get("facing")),
        "lease_duration": _pick_best(regex.get("lease_duration"), model.get("lease_duration")),
        "amenities": _pick_best(regex.get("amenities"), model.get("amenities")),
        "available_from": _pick_best(regex.get("available_from"), model.get("available_from")),

        # Model-first fields (model is better at these)
        "location": _pick_best(model.get("location"), regex.get("location")),
        "gated_community": model.get("gated_community") if model.get("gated_community") is not None else regex.get("gated_community"),
        "furnished": model.get("furnished") if model.get("furnished") else regex.get("furnished"),
    }

    # Layer 4: Keyword enrichment (listing_type, food, gender, brokerage)
    result["raw_text"] = text
    result = enrich_listing(result)

    return result


if __name__ == "__main__":
    tests = [
        "3BHK fully furnished flat in gated society Mantri Celestia, Wipro circle. Rent 17,666. Deposit 34000. Lift, gym, swimming pool. Move in 1st May. Call 9876543210",
        "1RK semi furnished in Kondapur. 12k rent. No brokerage. Vegetarian preferred. Female only.",
        "Looking for male flatmate in 2bhk at Prestige High Fields. 8k per person. Immediate move in. Parking, wifi, ac available.",
    ]
    for t in tests:
        print(f"\nInput: {t[:70]}...")
        result = parse_listing_cascade(t)
        for k, v in result.items():
            if k != "raw_text" and v is not None:
                print(f"  {k}: {v}")
