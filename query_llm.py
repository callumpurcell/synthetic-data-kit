import os
import glob
import json
import yaml
from openai import OpenAI
from parse_args import parse_args

def load_prompts(config_path):
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    return (
        data['prompts']['system_prompt_one_table'],
        data['prompts']['q_generation_one_table'],
        data['prompts']['code_generation_one_table']
    )

def read_text_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def get_question_for_file(base, args):
    # Determine question file path based on args
    if args.question_file:
        return args.question_file
    if args.question_dir:
        return os.path.join(args.question_dir, f"{base}_questions.json")
    raise ValueError("In code mode, either --question-file or --question-dir must be provided.")

def generate_prompt(mode, page_text, q_prompt, code_prompt, args, base=None):
    if mode == 'question':
        return q_prompt.format(text=page_text)
    # code mode: load corresponding question
    q_path = get_question_for_file(base, args)
    with open(q_path, 'r', encoding='utf-8') as f:
        q_data = json.load(f)
    question = q_data.get('Question')
    return code_prompt.format(text=page_text, question=question)

def save_output(output, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        try:
            parsed = json.loads(output)
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            f.write(output)

def save_reasoning(reasoning, output_path):
    if reasoning:
        reason_file = output_path.replace('.json', '_reasoning.txt')
        with open(reason_file, 'w', encoding='utf-8') as f:
            f.write(reasoning)
        print(f"Reasoning saved to {reason_file}")

def process_file(file_path, args, prompts, client):
    system_prompt, q_prompt, code_prompt = prompts
    filename = os.path.basename(file_path)
    base, _ = os.path.splitext(filename)

    page_text = read_text_file(file_path)
    filled_prompt = generate_prompt(
        args.mode, page_text, q_prompt, code_prompt, args, base=base
    )

    suffix = 'questions' if args.mode == 'question' else 'code'
    output_filename = f"{base}_{suffix}.json"
    output_path = os.path.join(args.output_dir, output_filename)

    response = client.chat.completions.create(
        model='Qwen/Qwen3-0.6B',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': filled_prompt}
        ],
        temperature=0.7,
        top_p=0.95,
        max_tokens=4096
    )

    msg = response.choices[0].message
    output = msg.content.strip()
    reasoning = getattr(msg, 'reasoning_content', None)

    save_output(output, output_path)
    print(f"Generated output saved to {output_path}")
    save_reasoning(reasoning, output_path)

    return output_path


def main():
    args = parse_args()
    prompts = load_prompts(args.config)
    client = OpenAI(api_key='EMPTY', base_url='http://localhost:8000/v1')

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Decide on text files to process
    if args.input_file:
        files = [args.input_file]
    else:
        files = glob.glob(os.path.join(args.input_dir, '*.txt'))

    # Validate question inputs for code mode
    if args.mode == 'code':
        if args.input_file and not args.question_file:
            raise ValueError("--question-file required when using --input-file in code mode.")
        if args.input_dir and not args.question_dir:
            raise ValueError("--question-dir required when using --input-dir in code mode.")

    for file_path in files:
        process_file(file_path, args, prompts, client)

if __name__ == '__main__':
    main()