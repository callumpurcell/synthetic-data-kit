import os
import glob
import json
from parse_args import parse_args, classify_paths
from utils import load_prompts, read_text_file, get_question_for_file
from prompt_builder import generate_prompt


def build_requests_for_file(file_path, args, prompts):
    """
    For a single text file, generate args.num_questions separate chat‐completion
    payloads (each with its own custom_id). Returns a list of dicts like:
      { "custom_id": "...", "body": { ... } }
    """
    system_prompt, q_prompt, _ = prompts
    base = os.path.splitext(os.path.basename(file_path))[0]
    text = read_text_file(file_path)

    prev_questions = []
    batch_reqs = []

    for i in range(args.num_questions):
        # Build the prompt (but do NOT call the API here)
        prompt = generate_prompt(
            'question', text, q_prompt, None, args, base, previous_questions=prev_questions
        )

        # Use a composite custom_id, e.g. "<base>_<i>"
        custom_id = f"{base}_{i}"
        batch_reqs.append({
            "custom_id": custom_id,
            "body": {
                "model": "mistral-small-2409",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": prompt}
                ],
                "temperature": 0.7,
                "top_p": 0.95,
                "max_tokens": 4096
            }
        })

        # Insert a placeholder so generate_prompt still runs if it expects previous_questions
        prev_questions.append({"Question": f"__PENDING_{base}_{i}__"})

    return batch_reqs


def main():
    args = parse_args()
    args = classify_paths(args)
    os.makedirs(args.output_dir, exist_ok=True)

    prompts = load_prompts(args.config)
    files = [args.input_file] if args.input_file else glob.glob(os.path.join(args.input_dir, '*.txt'))

    all_requests = []

    # Build up one big list of {custom_id, body} for every file + question
    for fp in files:
        if args.mode == 'question':
            reqs = build_requests_for_file(fp, args, prompts)
            all_requests.extend(reqs)
        else:
            # If you also need code‐generation batches, you could write a
            # build_requests_for_code_file(...) analogously and extend here.
            pass

    # Now write a single JSONL file containing every request
    batch_filename = os.path.join(args.output_dir, "batch_requests.jsonl")
    with open(batch_filename, 'w', encoding='utf-8') as fout:
        for req in all_requests:
            fout.write(json.dumps(req) + "\n")

    print(f"Wrote {len(all_requests)} lines to {batch_filename}")


if __name__ == '__main__':
    main()
