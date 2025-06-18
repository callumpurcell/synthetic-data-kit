import os
import json
import yaml


def load_prompts(config_path):
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    return (
        data['prompts']['system_prompt_reasoning'],
        data['prompts']['q_generation_5T1Q'],
        data['prompts']['reasoning_generation']
    )


def read_text_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


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
        fn = output_path.replace('.json', '_reasoning.txt')
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(reasoning)
        print(f"Reasoning saved to {fn}")


def get_question_for_file(base, args):
    if args.question_file:
        return args.question_file
    return os.path.join(args.question_dir, f"{base}_questions.json")