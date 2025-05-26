import argparse
import json
import yaml
from openai import OpenAI


def main():
    parser = argparse.ArgumentParser(
        description="Perform code generation or question generation based on configured prompts."
    )
    parser.add_argument(
        '--mode',
        choices=['code', 'question'],
        required=True,
        help='Select "code" for code generation or "question" for question generation.'
    )
    parser.add_argument(
        '--config',
        default='configs/config_ey.yaml',
        help='Path to the YAML configuration file.'
    )
    parser.add_argument(
        '--text-file',
        default='data/output/initial_042.txt',
        help='Path to the input text file.'
    )
    parser.add_argument(
        '--question-json',
        default='data/qwen_gen/output_questions.json',
        help='Path to the JSON file containing the question (only for code mode).'
    )
    parser.add_argument(
        '--output',
        help='Path to the output file where the generated JSON will be saved.'
    )
    args = parser.parse_args()

    # Load config
    with open(args.config, 'r') as f:
        data = yaml.safe_load(f)
    system_prompt = data['prompts']['system_prompt_one_table']
    q_prompt = data['prompts']['q_generation_one_table']
    code_prompt = data['prompts']['code_generation_one_table']

    # Read text
    with open(args.text_file, 'r', encoding='utf-8') as f:
        page_text = f.read()

    # Determine mode
    if args.mode == 'question':
        # Fill question prompt
        filled_prompt = q_prompt.format(text=page_text)
        default_out = 'data/qwen_gen/output_questions.json'
    else:
        # Load existing question for code generation
        with open(args.question_json, 'r', encoding='utf-8') as f:
            q_data = json.load(f)
        question = q_data.get('Question')
        filled_prompt = code_prompt.format(text=page_text, question=question)
        default_out = 'data/qwen_gen/output_code.json'

    output_path = args.output or default_out

    # Initialize client
    client = OpenAI(
        api_key='EMPTY',
        base_url='http://localhost:8000/v1'
    )

    # Send prompt
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

    # Extract content
    msg = response.choices[0].message
    output = msg.content.strip()
    reasoning = getattr(msg, 'reasoning_content', None)

    # Save output JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        try:
            parsed = json.loads(output)
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            f.write(output)
    print(f"Generated output saved to {output_path}")

    # Optionally save reasoning
    if reasoning:
        reason_file = output_path.replace('.json', '_reasoning.txt')
        with open(reason_file, 'w', encoding='utf-8') as f:
            f.write(reasoning)
        print(f"Reasoning saved to {reason_file}")


if __name__ == '__main__':
    main()
