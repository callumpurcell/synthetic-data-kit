#!/usr/bin/env python3
import os
import glob
import json
import traceback
import argparse

def safe_execute(code_str, global_ns=None):
    """
    Executes the given Python code string in a restricted namespace,
    capturing the variable `ans` if set. Returns ans or raises.
    """
    ns = {} if global_ns is None else dict(global_ns)
    try:
        exec(code_str, {}, ns)
        return ns.get('ans')
    except Exception:
        tb = traceback.format_exc()
        raise RuntimeError(f"Execution failed: {tb}")

def process_code_output(file_path, output_dir=None):
    """
    - Loads the JSON list from `file_path`.
    - For each entry: runs safe_execute(...), then immediately tests json.dumps(answer).
      • If safe_execute(...) fails => record error in this entry’s "Error" and set answer=None.
      • Else if json.dumps(answer) fails => record that TypeError in "Error" and set answer=None.
      • Otherwise, store the clean answer and leave "Error": null.
    - Appends every entry to `results`.  Never skips the entire file—only the bad entry is marked.
    - Finally writes results out to *_with_answers.json (where each entry has "Answer" and/or "Error").
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = []
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            print(f"Skipping invalid entry at index {idx}: expected dict, got {type(entry).__name__}")
            continue

        question     = entry.get('Question')
        explanation  = entry.get('Explanation')
        code_snippet = entry.get('Python_code')
        reasoning    = entry.get('Reasoning')

        answer = None
        error  = None

        if code_snippet:
            # 1) Try to execute the snippet
            try:
                raw_ans = safe_execute(code_snippet)
            except Exception as e:
                error = f"Execution failed: {str(e).splitlines()[-1]}"
                results.append({
                    'Question': question,
                    'Explanation': explanation,
                    'Python_code': code_snippet,
                    'Answer': None,
                    'Reasoning': reasoning,
                    'Error': error
                })
                # Move on to next entry
                continue

            # 2) Now test serializability of raw_ans
            try:
                # Attempt to JSON-serialize the answer alone
                json.dumps(raw_ans)
                # If that works, we keep raw_ans as-is
                answer = raw_ans
            except TypeError as e:
                error = f"Non-serializable answer: {e}"
                answer = None

        else:
            # No snippet provided
            error = "No code snippet provided"

        results.append({
            'Question': question,
            'Explanation': explanation,
            'Python_code': code_snippet,
            'Answer': answer,
            'Reasoning': reasoning,
            'Error': error
        })

    # Determine output path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{base_name}_with_answers.json")
    else:
        out_path = os.path.join(os.path.dirname(file_path), f"{base_name}_with_answers.json")

    # Write all entries—good ones and the one with serialization error—
    # so you end up saving four correct entries plus one with {"Answer": null, "Error": "..."}
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved executed results to {out_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Execute Python snippets inside *_code.json files and write results to JSON. "
                    "For any entry whose `ans` is not JSON‐serializable, store that error in `Error` and set Answer to null."
    )
    parser.add_argument(
        "--input-dir", "-i",
        default=os.getcwd(),
        help="Directory to look for *_code.json files (default: current working directory)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Directory to save *_with_answers.json files (default: same folder as each input file)"
    )
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir) if args.output_dir else None

    pattern = os.path.join(input_dir, "*_code.json")
    matches = glob.glob(pattern)
    if not matches:
        print(f"No files matching '*_code.json' found in '{input_dir}'.")
        return

    for file_path in matches:
        process_code_output(file_path, output_dir=output_dir)

if __name__ == "__main__":
    main()
