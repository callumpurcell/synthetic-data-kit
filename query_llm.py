import os
import glob
from openai import OpenAI

from parse_args import parse_args, classify_paths
from utils import load_prompts, read_text_file, save_output, save_reasoning
from prompt_builder import generate_prompt


def process_file(file_path, args, prompts, client):
    system, q_prompt, code_prompt = prompts
    base = os.path.splitext(os.path.basename(file_path))[0]
    text = read_text_file(file_path)

    try:
        prompt = generate_prompt(args.mode, text, q_prompt, code_prompt, args, base)
    except (FileNotFoundError, ValueError) as e:
        print(f"Skipping {file_path}: {e}")
        return

    out_fn = f"{base}_{'questions' if args.mode=='question' else 'code'}.json"
    out_path = os.path.join(args.output_dir, out_fn)

    try:
        resp = client.chat.completions.create(
            model='Qwen/Qwen3-0.6B',
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user',   'content': prompt}
            ],
            temperature=0.7, top_p=0.95, max_tokens=4096
        )
        msg = resp.choices[0].message
        if not msg or not getattr(msg, 'content', None):
            print(f"No valid message for {file_path}, skipping.")
            return
        output, reasoning = msg.content.strip(), getattr(msg, 'reasoning_content', None)
    except Exception as e:
        print(f"Error on {file_path}: {e}")
        return

    save_output(output, out_path)
    print(f"Generated output saved to {out_path}")
    save_reasoning(reasoning, out_path)


def main():
    args = parse_args()
    args = classify_paths(args)
    os.makedirs(args.output_dir, exist_ok=True)

    prompts = load_prompts(args.config)
    client  = OpenAI(api_key='EMPTY', base_url='http://localhost:8000/v1')

    files = [args.input_file] if args.input_file else glob.glob(os.path.join(args.input_dir, '*.txt'))
    for fp in files:
        process_file(fp, args, prompts, client)

if __name__ == '__main__':
    main()