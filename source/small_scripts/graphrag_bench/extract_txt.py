import json
import os

# Path to your input JSON file
INPUT_JSON = "novel_clean.json"
# INPUT_JSON = "medical_clean.json"
OUTPUT_DIR = "data"

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Read the JSON file
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# Process each item
for item in data:
    corpus_name = item.get("corpus_name", "unknown")
    context = item.get("context", "")

    # Construct output file path
    output_path = os.path.join(OUTPUT_DIR, f"{corpus_name}.txt")

    # Write the context to the file
    with open(output_path, "w", encoding="utf-8") as out_f:
        out_f.write(context)

    print(f"Wrote: {output_path}")
