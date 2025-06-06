import os
import glob
import json
import time
from mistralai import Mistral
from mistralai.models.sdkerror import SDKError

from parse_args import parse_args, classify_paths
from utils import load_prompts, read_text_file, save_output, save_reasoning, get_question_for_file
from prompt_builder import generate_prompt


def call_with_rate_limit_retries(func, *, max_retries=3, backoff=2.0):
    """
    Helper: call `func()` once. If it raises an SDKError whose text contains "rate limit",
    sleep for `backoff` seconds and retry, up to `max_retries` times total.
    """
    attempt = 0
    while True:
        try:
            return func()
        except SDKError as e:
            text = str(e).lower()
            # detect rate-limit error by presence of "rate limit" or HTTP 429 in message
            if ("rate limit" in text or "429" in text) and attempt < max_retries:
                attempt += 1
                wait = backoff * attempt
                print(f"→ Rate limit hit. Backing off for {wait:.1f}s (attempt {attempt}/{max_retries})…")
                time.sleep(wait)
                continue
            else:
                raise  # re-raise if not a rate limit or if we've exhausted retries


def process_question_file(file_path, args, prompts, client):
    system_prompt, q_prompt, _ = prompts
    base = os.path.splitext(os.path.basename(file_path))[0]
    text = read_text_file(file_path)

    prev_questions = []  # list of {'Question': ...}
    for i in range(args.num_questions):
        # Sleep for slightly >1s to avoid drifting into a 429
        time.sleep(1.2)

        prompt = generate_prompt(
            'question', text, q_prompt, None, args, base, previous_questions=prev_questions
        )
        try:
            # Wrap the actual API call so we can catch 429s and retry
            resp = call_with_rate_limit_retries(
                lambda: client.chat.complete(
                    model="mistral-large-2411",
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user',   'content': prompt}
                    ],
                    temperature=0.7,
                    top_p=0.95,
                    max_tokens=4096
                )
            )
            msg = resp.choices[0].message
            out = msg.content.strip() if msg and getattr(msg, 'content', None) else ''
        except Exception as e:
            print(f"Error generating question #{i+1} for {file_path}: {e}")
            continue  # skip this iteration

        # ——— PREPROCESS: strip any ```json or ``` code fences ———
        cleaned = out.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        # ——— Attempt to parse JSON from the (possibly-unfenced) string ———
        try:
            data = json.loads(cleaned)
            items = data if isinstance(data, list) else [data]
        except json.JSONDecodeError as err:
            print(
                f"Invalid JSON for question #{i+1}, skipping this one. Error: {err}\n"
                f"Raw (preprocessed) output:\n{cleaned}\n"
                f"Original output:\n{out}"
            )
            continue

        # append new unique questions
        for item in items:
            if isinstance(item, dict) and 'Question' in item:
                qtext = item['Question']
            elif isinstance(item, str):
                qtext = item
            else:
                continue
            if not any(q['Question'] == qtext for q in prev_questions):
                prev_questions.append({'Question': qtext})

        if len(prev_questions) >= args.num_questions:
            break

    # save all questions in one JSON
    out_fn = f"{base}_questions.json"
    out_path = os.path.join(args.output_dir, out_fn)
    save_output(json.dumps(prev_questions), out_path)
    print(f"Saved {len(prev_questions)} questions to {out_path}")


def process_code_file(file_path, args, prompts, client):
    system_prompt, q_prompt, code_prompt = prompts
    base = os.path.splitext(os.path.basename(file_path))[0]
    text = read_text_file(file_path)

    # load list of questions
    q_path = get_question_for_file(base, args)
    try:
        with open(q_path, 'r', encoding='utf-8') as f:
            q_list = json.load(f)
        if not isinstance(q_list, list):
            raise ValueError('Question file must be a JSON list')
    except Exception as e:
        print(f"Skipping code gen for {file_path}: {e}")
        return

    responses = []  # collect all code outputs
    for idx, item in enumerate(q_list, start=1):
        # Sleep a bit over 2 s between code-generation calls
        time.sleep(2.2)

        question = item['Question'] if isinstance(item, dict) else item
        filled = code_prompt.format(text=text, question=question)

        try:
            resp = call_with_rate_limit_retries(
                lambda: client.chat.complete(
                    model="mistral-large-2411",
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user',   'content': filled}
                    ],
                    temperature=0,
                    top_p=1,
                    max_tokens=4096
                )
            )
            msg = resp.choices[0].message
            raw_output = msg.content.strip() if msg and getattr(msg, 'content', None) else None
            reasoning = getattr(msg, 'reasoning_content', None)
        except Exception as e:
            print(f"Error generating code for question #{idx} in {file_path}: {e}")
            continue

        if not raw_output:
            print(f"No output for question #{idx}, skipping.")
            continue

        # strip markdown fences if present
        clean_output = raw_output
        if clean_output.startswith("```"):
            fence_lines = clean_output.splitlines()
            fence_lines = fence_lines[1:]
            if fence_lines and fence_lines[-1].startswith("```"):
                fence_lines = fence_lines[:-1]
            clean_output = "".join(fence_lines)

        # remove optional leading language tag (e.g., 'json')
        stripped = clean_output.lstrip()
        if stripped.lower().startswith('json'):
            stripped = stripped[len('json'):].lstrip(':').lstrip()
        clean_output = stripped

        try:
            parsed = json.loads(clean_output)
            explanation = parsed.get('Explanation') or parsed.get('explanation')
            code_block = (
                parsed.get('Python_code')
                or parsed.get('Python code')
                or parsed.get('code')
                or parsed.get('Code')
            )
            entry = {'Question': question}
            if explanation is not None:
                entry['Explanation'] = explanation
            if code_block is not None:
                entry['Python_code'] = code_block
            entry['Reasoning'] = reasoning
        except json.JSONDecodeError:
            print(f"Invalid JSON response for question #{idx}, storing raw under 'Response'.")
            entry = {
                'Question': question,
                'Response': raw_output,
                'Reasoning': reasoning
            }
        responses.append(entry)

    # save all code responses to a single JSON
    out_fn = f"{base}_code.json"
    out_path = os.path.join(args.output_dir, out_fn)
    save_output(json.dumps(responses), out_path)
    print(f"Saved {len(responses)} code responses to {out_path}")


def main():
    args = parse_args()
    args = classify_paths(args)
    os.makedirs(args.output_dir, exist_ok=True)

    prompts = load_prompts(args.config)
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise EnvironmentError("Please set the MISTRAL_API_KEY environment variable.")
    client = Mistral(api_key=api_key)

    files = [args.input_file] if args.input_file else glob.glob(os.path.join(args.input_dir, '*.txt'))
    for fp in files:
        if args.mode == 'question':
            process_question_file(fp, args, prompts, client)
        else:
            process_code_file(fp, args, prompts, client)


if __name__ == '__main__':
    main()
