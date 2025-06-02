#!/usr/bin/env python3
import os
import glob
import json
import csv
import argparse

def load_txt_content(txt_path):
    """Read entire .txt file and return it as a single string."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Could not read '{txt_path}': {e}")

def process_one_json(json_path, txt_dir):
    """
    Given a path like /somewhere/first_012_code_with_answers.json,
    find /otherwhere/first_012.txt, read both, and return a list of rows:
    [ [txt_content, question, answer, explanation, reasoning, error], ... ].
    """
    base_filename = os.path.basename(json_path)                  # e.g. "first_012_code_with_answers.json"
    prefix = base_filename.replace("_code_with_answers.json", "")  # e.g. "first_012"
    txt_filename = prefix + ".txt"                                # e.g. "first_012.txt"
    txt_path = os.path.join(txt_dir, txt_filename)

    if not os.path.isfile(txt_path):
        raise FileNotFoundError(f"Expected text file not found: {txt_path}")

    # 1) read the .txt once
    txt_content = load_txt_content(txt_path)

    # 2) read the JSON list
    with open(json_path, 'r', encoding='utf-8') as jf:
        data = json.load(jf)

    rows = []
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            # skip any non‐dict entries
            continue

        question    = entry.get("Question", "") or ""
        answer      = entry.get("Answer", "")
        code = entry.get("Python_code", "") or ""
        explanation = entry.get("Explanation", "") or ""
        reasoning   = entry.get("Reasoning", "") or ""
        error       = entry.get("Error", "") or ""

        # Convert answer to string (so that e.g. numeric values become "6")
        answer_str = "" if answer is None else str(answer)

        rows.append([
            txt_content,
            question,
            answer_str,
            explanation,
            code,
            reasoning,
            error
        ])

    return rows

def main():
    parser = argparse.ArgumentParser(
        description="Combine first_xxx.txt contents + first_xxx_code_with_answers.json entries into one CSV."
    )
    parser.add_argument(
        "--json-dir", "-j",
        required=True,
        help="Directory containing files named first_{xxx}_code_with_answers.json"
    )
    parser.add_argument(
        "--txt-dir", "-t",
        required=True,
        help="Directory containing files named first_{xxx}.txt"
    )
    parser.add_argument(
        "--output-csv", "-o",
        default="combined_dataset.csv",
        help="Path to the output CSV file (default: combined_dataset.csv)"
    )
    args = parser.parse_args()

    json_dir = os.path.abspath(args.json_dir)
    txt_dir = os.path.abspath(args.txt_dir)
    out_csv = os.path.abspath(args.output_csv)

    # 1) Find all matching JSON files under json_dir
    pattern = os.path.join(json_dir, "first_*_code_with_answers.json")
    all_json = sorted(glob.glob(pattern))

    if not all_json:
        print(f"Warning: No files matching 'first_*_code_with_answers.json' found in '{json_dir}'.")
        return

    # 2) Open CSV for writing (overwrite if exists)
    with open(out_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow([
            "txt_content",
            "question",
            "answer",
            "explanation",
            "code",
            "reasoning",
            "error"
        ])

        # 3) Process each JSON in turn
        for json_path in all_json:
            try:
                rows = process_one_json(json_path, txt_dir)
            except FileNotFoundError as fnf:
                print(f"Skipping '{os.path.basename(json_path)}': {fnf}")
                continue
            except Exception as e:
                print(f"Error reading '{json_path}': {e}")
                continue

            # 4) Write each row (one per JSON entry) to CSV
            for row in rows:
                writer.writerow(row)

    print(f"Done.  Wrote {out_csv} with {len(all_json)} JSON files worth of rows.")


if __name__ == "__main__":
    main()
