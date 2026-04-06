# export_training_data.py
"""Export DB listings as training data for finetuning."""
import sqlite3
import json

DB_FILE = "listings.db"
OUTPUT_FILE = "training_data.jsonl"

# Fields the model should extract (regex handles the rest)
MODEL_FIELDS = ["gated_community", "furnished", "available_from", "amenities"]


def build_training_pair(row):
    """Build a single training example from a DB row."""
    raw_text = row["raw_text"]
    if not raw_text or len(raw_text) < 30:
        return None

    # Build expected output from DB values
    output = {}
    for field in MODEL_FIELDS:
        val = row[field]
        if field == "amenities" and val:
            try:
                val = json.loads(val) if isinstance(val, str) else val
            except (json.JSONDecodeError, TypeError):
                val = None
        if field == "gated_community":
            val = bool(val) if val is not None else None
        output[field] = val

    # Skip if all fields are None
    if all(v is None for v in output.values()):
        return None

    prompt = f"""Extract these fields from the flat rental post. Return JSON only.
Fields: gated_community (bool), furnished ("fully"/"semi"/"unfurnished"), available_from (date/string), amenities (list)
Use null for missing values.

Post: {raw_text}"""

    return {
        "prompt": prompt,
        "completion": json.dumps(output, ensure_ascii=False)
    }


def main():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM listings").fetchall()
    conn.close()

    examples = []
    for row in rows:
        pair = build_training_pair(dict(row))
        if pair:
            examples.append(pair)

    with open(OUTPUT_FILE, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"Exported {len(examples)} training examples to {OUTPUT_FILE}")

    # Also export in chat format for models that need it
    chat_file = "training_data_chat.jsonl"
    with open(chat_file, "w") as f:
        for ex in examples:
            chat = {
                "messages": [
                    {"role": "system", "content": "You extract flat rental info from Facebook posts. Return JSON only."},
                    {"role": "user", "content": ex["prompt"]},
                    {"role": "assistant", "content": ex["completion"]}
                ]
            }
            f.write(json.dumps(chat, ensure_ascii=False) + "\n")

    print(f"Exported {len(examples)} chat examples to {chat_file}")


if __name__ == "__main__":
    main()
