import os
import glob
import json
import traceback

def safe_execute(code_str, global_ns=None):
    """
    Executes the given Python code string in a restricted namespace,
    capturing the variable `ans` if set. Returns ans or raises.
    """
    # Prepare a clean namespace
    ns = {} if global_ns is None else dict(global_ns)
    try:
        exec(code_str, {}, ns)
        return ns.get('ans')
    except Exception:
        # propagate error with traceback
        tb = traceback.format_exc()
        raise RuntimeError(f"Execution failed: {tb}")


def process_code_output(file_path):
    base = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = []
    for idx, entry in enumerate(data):
        # ensure entry is a dict
        if not isinstance(entry, dict):
            print(f"Skipping invalid entry at index {idx}: expected dict, got {type(entry).__name__}")
            continue

        question = entry.get('Question')
        explanation = entry.get('Explanation')
        code_snippet = entry.get('Python_code')
        reasoning = entry.get('Reasoning')

        answer = None
        error = None
        if code_snippet:
            try:
                answer = safe_execute(code_snippet)
            except Exception as e:
                error = str(e)

        results.append({
            'Question': question,
            'Explanation': explanation,
            'Python_code': code_snippet,
            'Answer': answer,
            'Reasoning': reasoning,
            'Error': error
        })

    # Write results to disk
    out_fn = f"{base}_with_answers.json"
    out_path = os.path.join(os.path.dirname(file_path), out_fn)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved executed results to {out_path}")


def main():
    # assume code-mode JSON files end with '_code.json'
    cwd = os.getcwd()
    for file_path in glob.glob(os.path.join(cwd, '*_code.json')):
        process_code_output(file_path)

if __name__ == '__main__':
    main()